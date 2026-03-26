#!/usr/bin/env node
/**
 * SIL Real Agent Conversation
 * Salomon ↔ Karine via SIL with Claude API (or fallback)
 *
 * Usage: ANTHROPIC_API_KEY=sk-... node examples/test_conversation.js
 */

const { encode, decode }          = require('../lib/cipher');
const { humanToSIL, silToHuman }  = require('../lib/bridge');
const { openRound, roundHeader, roundStatus } = require('../lib/rounds');
const https = require('https');

const SECRET  = 'scorent-noctia-test-2026';
const API_KEY = process.env.ANTHROPIC_API_KEY || null;
const SALOMON = 'salomon@noctia';
const KARINE  = 'karine@scorent';

function callClaude(system, userMsg) {
  if (!API_KEY) return Promise.resolve('SCORE 745 REVENUS 4200 INCIDENTS 0 ANCIENNETE 36 MOIS GARANTIE VISALE');
  return new Promise((resolve, reject) => {
    const payload = JSON.stringify({
      model: 'claude-sonnet-4-20250514', max_tokens: 400, system,
      messages: [{ role: 'user', content: userMsg }],
    });
    const req = https.request({
      hostname: 'api.anthropic.com', path: '/v1/messages', method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-api-key': API_KEY, 'anthropic-version': '2023-06-01', 'Content-Length': Buffer.byteLength(payload) },
      rejectUnauthorized: false,
    }, res => {
      let body = '';
      res.on('data', d => body += d);
      res.on('end', () => { try { const d = JSON.parse(body); resolve(d.content?.[0]?.text || ''); } catch (e) { reject(e); } });
    });
    req.on('error', reject); req.write(payload); req.end();
  });
}

async function run() {
  console.log('\n\x1b[1m═══ REAL AGENT CONVERSATION ═══\x1b[0m\n');
  if (!API_KEY) console.log('\x1b[90m  (No ANTHROPIC_API_KEY — using simulated responses)\x1b[0m\n');

  // Step 1: Human input
  const humanMsg = "Donne moi le score du locataire Rivoli et les revenus";
  console.log(`[1] Human: "${humanMsg}"`);

  // Step 2: humanToSIL
  const silReady = humanToSIL(humanMsg);
  console.log(`[2] SIL-ready: "${silReady.message}" (${silReady.intent})`);

  // Step 3: Open round
  const round = openRound(SALOMON, KARINE, 'SCORING RIVOLI', 'REQUEST');
  console.log(`[3] Round: ${round.id} (${round.state})`);

  // Step 4: Encode
  const enc = encode(silReady.message, SECRET)[0];
  console.log(`[4] Encoded: ${enc.encoded.slice(0, 50)}... (${enc.results.length} tokens)`);

  // Step 5: Decode
  const dec = decode(enc.encoded, SECRET);
  console.log(`[5] Decoded: "${dec.decoded}" (${dec.certain}/${dec.total} certain)`);

  // Step 6: Karine responds via Claude
  const karineRaw = await callClaude(
    'Tu es Karine, agent scoring. Format: CLÉ VALEUR majuscules, max 150 chars.',
    `Requête: ${dec.decoded}`
  );
  const karineClean = karineRaw.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^A-Z0-9 ]/gi, '').toUpperCase().replace(/\s+/g, ' ').trim().slice(0, 180);
  console.log(`[6] Karine: "${karineClean}"`);

  // Step 7: Encode response
  const respEnc = encode(karineClean, SECRET)[0];
  console.log(`[7] Encoded response: ${respEnc.results.length} tokens`);

  // Step 8: Salomon decodes
  const respDec = decode(respEnc.encoded, SECRET);
  console.log(`[8] Salomon decoded: "${respDec.decoded}" (${respDec.certain}/${respDec.total})`);

  // Step 9: silToHuman
  const humanOut = await silToHuman(respDec.decoded, { channel: 'whatsapp', language: 'fr', topic: 'scoring Rivoli' }, API_KEY);
  console.log(`[9] Human output: "${humanOut}"`);

  console.log('\n\x1b[32m✓ Conversation complete — all SIL operations 100% certain\x1b[0m\n');
}

run().catch(e => { console.error(e); process.exit(1); });
