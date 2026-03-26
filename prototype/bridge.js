/**
 * SIL Human Bridge v1.0
 * 
 * Bidirectional bridge between human channels and SIL.
 * 
 * Human → SIL:
 *   Natural language → ZMF structured payload → SIL encoded
 *
 * SIL → Human:
 *   SIL decoded → structured data → natural language (via Claude)
 *   "SCORE 745 REVENUS 4200 INCIDENTS 0"
 *   → "L'appartement Rivoli affiche un score de 745/1000,
 *      des revenus de 4 200€/mois et aucun incident
 *      sur les 12 derniers mois."
 */

const crypto  = require('crypto');
const https   = require('https');

// ============================================================
// HUMAN → ZMF (intent detection)
// ============================================================

const INTENT_KEYWORDS = {
  REQUEST:     ['solde', 'score', 'analyse', 'donne', 'montre', 'dis', 'cherche', 'trouve', 'où en sont', 'comment va', 'quel est', 'combien'],
  OFFER:       ['propose', 'offre', 'je veux', 'je peux', 'disponible', 'tarif', 'prix'],
  ALERT:       ['urgent', 'alerte', 'problème', 'incident', 'attention', 'erreur', 'stop'],
  NEGOTIATION: ['négocie', 'contre-proposition', 'discount', 'réduction', 'accord'],
  INFO:        [],  // default
};

function detectIntent(text) {
  const lower = text.toLowerCase();
  for (const [intent, keywords] of Object.entries(INTENT_KEYWORDS)) {
    if (keywords.some(k => lower.includes(k))) return intent;
  }
  return 'INFO';
}

/**
 * Convert natural language to SIL-ready structured message.
 * Strips human noise: greetings, punctuation, filler words.
 */
function humanToSIL(humanText) {
  // Remove common noise
  let clean = humanText
    .replace(/^(salomon|karine|moise|hey|bonjour|bonsoir|merci|svp|stp)[,\s]*/gi, '')
    .replace(/[?!.,;:]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .toUpperCase();

  // Limit to 180 chars for single-chunk encoding
  if (clean.length > 180) clean = clean.slice(0, 180).trim();

  const intent = detectIntent(humanText);

  return { message: clean, intent };
}

// ============================================================
// SIL → HUMAN (noise reintroduction via Claude)
// ============================================================

/**
 * Call Claude API to convert SIL cold response to natural language.
 * SSL fix included for Mac.
 */
function silToHuman(silDecoded, context = {}, apiKey = null) {
  return new Promise((resolve) => {
    if (!apiKey) {
      // Fallback: basic formatting without LLM
      resolve(silDecoded
        .replace(/(\w+) (\d+)/g, '$1 : $2')
        .toLowerCase()
        .replace(/\b\w/g, c => c.toUpperCase()));
      return;
    }

    const { channel = 'whatsapp', language = 'fr', topic = '' } = context;

    const system = `Tu es Salomon, assistant IA. Tu reçois des données brutes d'un autre agent et tu les reformules en message naturel pour un humain sur ${channel}.

RÈGLES :
- Réponse courte (2-4 phrases max)
- Ton professionnel mais chaleureux
- Format adapté à ${channel} (pas de markdown sur WhatsApp)
- Langue : ${language}
- Contexte : ${topic}
- Ne commence pas par "Bien sûr" ou "Voici"`;

    const payload = JSON.stringify({
      model:      'claude-sonnet-4-20250514',
      max_tokens: 300,
      system,
      messages: [{ role: 'user', content: `Données reçues : ${silDecoded}` }],
    });

    const options = {
      hostname: 'api.anthropic.com',
      path:     '/v1/messages',
      method:   'POST',
      headers: {
        'Content-Type':      'application/json',
        'x-api-key':         apiKey,
        'anthropic-version': '2023-06-01',
        'Content-Length':    Buffer.byteLength(payload),
      },
      rejectUnauthorized: false,  // SSL fix Mac
    };

    const req = https.request(options, (res) => {
      let body = '';
      res.on('data', d => { body += d; });
      res.on('end', () => {
        try {
          const data = JSON.parse(body);
          resolve(data.content?.[0]?.text || silDecoded);
        } catch (e) {
          resolve(silDecoded);
        }
      });
    });

    req.on('error', () => resolve(silDecoded));
    req.write(payload);
    req.end();
  });
}

// ============================================================
// FULL BRIDGE FLOW
// ============================================================

/**
 * Process a human message through the full bridge:
 * human text → SIL-ready payload (ready to encode + send)
 */
function processHumanInput(humanText, senderAgentId, recipientAgentId) {
  const { message, intent } = humanToSIL(humanText);
  return {
    original:  humanText,
    message,
    intent,
    sender:    senderAgentId,
    recipient: recipientAgentId,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Process a SIL response for human delivery:
 * decoded SIL → natural language on human channel
 */
async function processForHuman(silDecoded, context = {}, apiKey = null) {
  const natural = await silToHuman(silDecoded, context, apiKey);
  return {
    sil_raw: silDecoded,
    human:   natural,
    channel: context.channel || 'text',
  };
}

module.exports = {
  humanToSIL,
  silToHuman,
  detectIntent,
  processHumanInput,
  processForHuman,
};
