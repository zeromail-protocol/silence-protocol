/**
 * SIL A2A Bridge v1.0
 * 
 * Makes SIL content travel inside A2A messages.
 * A2A agents without SIL see an opaque data part.
 * A2A agents with SIL decode the content.
 * 
 * Spec: https://a2a-protocol.org/latest/specification/
 * SIL is expressed as an A2A "data" Part with mediaType application/x-sil
 */

const crypto = require('crypto');
const { encode, decodeChunk, ALPHABETS } = require('./cipher');

const SIL_MEDIA_TYPE = 'application/x-sil';
const SIL_VERSION    = '1.5';

// ============================================================
// ENCODE SIL → A2A Part
// ============================================================

/**
 * Wrap a SIL-encoded message into an A2A-compliant Part object.
 * This is what an A2A client sends when it wants SIL confidentiality.
 *
 * @param {string} message   — plaintext message
 * @param {string} secret    — shared secret
 * @param {string} sender    — sender agent ID
 * @param {string} intent    — SIL intent (OFFER, REQUEST, INFO, ALERT, NEGOTIATION)
 * @returns {object}         — A2A Part + SIL metadata
 */
function encodeToA2APart(message, secret, sender, intent = 'INFO') {
  const chunks = encode(message, secret);
  const parts  = [];

  chunks.forEach((chunk) => {
    const msgId = crypto.createHash('sha256')
      .update(`${sender}${message}${Date.now()}${chunk.chunkIndex}`)
      .digest('hex').slice(0, 16);

    const silPayload = {
      'x-sil-version':   SIL_VERSION,
      'x-sil-sender':    sender,
      'x-sil-intent':    intent,
      'x-sil-message-id': msgId,
      'x-sil-chunk':     chunk.chunkIndex,
      'x-sil-chunks':    chunk.totalChunks,
      'x-sil-scripts':   chunk.langsUsed,
      'x-sil-checksum':  chunk.gklGlobal,
      'x-sil-encoded':   chunk.encoded,
      'x-sil-signature': crypto.createHash('sha256')
        .update(`${secret}${chunk.encoded}`)
        .digest('hex'),
    };

    // A2A Part — data type, mediaType application/x-sil
    parts.push({
      data:      silPayload,
      mediaType: SIL_MEDIA_TYPE,
      metadata: {
        'sil-intent':  intent,
        'sil-version': SIL_VERSION,
        'sil-chunk':   `${chunk.chunkIndex + 1}/${chunk.totalChunks}`,
      }
    });
  });

  return parts;
}

/**
 * Build a full A2A message/send request with SIL-encrypted content.
 * Compatible with A2A v1.0 JSON-RPC spec.
 */
function buildA2AMessage(message, secret, sender, recipient, intent = 'INFO', contextId = null) {
  const parts = encodeToA2APart(message, secret, sender, intent);
  const msgId = crypto.randomUUID();

  return {
    jsonrpc: '2.0',
    id:      crypto.randomUUID(),
    method:  'message/send',
    params: {
      message: {
        messageId: msgId,
        role:      'agent',
        contextId: contextId || crypto.randomUUID(),
        parts,
        metadata: {
          'x-protocol':    'SIL/1.5',
          'x-sil-sender':  sender,
          'x-sil-intent':  intent,
        }
      }
    }
  };
}

// ============================================================
// DECODE A2A Part → SIL message
// ============================================================

/**
 * Check if an A2A message contains SIL-encrypted parts.
 */
function hasSILParts(a2aMessage) {
  const parts = a2aMessage?.params?.message?.parts ||
                a2aMessage?.message?.parts || [];
  return parts.some(p => p.mediaType === SIL_MEDIA_TYPE);
}

/**
 * Extract and decode all SIL parts from an A2A message.
 * Returns decoded text and metadata.
 */
function decodeFromA2AMessage(a2aMessage, secret) {
  const parts = a2aMessage?.params?.message?.parts ||
                a2aMessage?.message?.parts || [];

  const silParts = parts.filter(p => p.mediaType === SIL_MEDIA_TYPE);

  if (!silParts.length) {
    return { isSIL: false, decoded: null, parts: [] };
  }

  const results = [];
  let fullDecoded = '';

  for (const part of silParts) {
    const sil = part.data;

    // Verify signature
    const expectedSig = crypto.createHash('sha256')
      .update(`${secret}${sil['x-sil-encoded']}`)
      .digest('hex');
    const sigOk = sil['x-sil-signature'] === expectedSig;

    if (!sigOk) {
      results.push({ error: 'INVALID_SIGNATURE', chunk: sil['x-sil-chunk'] });
      continue;
    }

    const chunkIndex = sil['x-sil-chunk'] || 0;
    const dec = decodeChunk(sil['x-sil-encoded'], secret, chunkIndex);

    results.push({
      chunkIndex,
      totalChunks: sil['x-sil-chunks'] || 1,
      intent:      sil['x-sil-intent'],
      sender:      sil['x-sil-sender'],
      messageId:   sil['x-sil-message-id'],
      scripts:     sil['x-sil-scripts'],
      decoded:     dec.decoded,
      certain:     dec.certain,
      total:       dec.total,
      integrity:   dec.integrity,
      sigOk,
    });

    fullDecoded += dec.decoded;
  }

  const intent  = results[0]?.intent || 'INFO';
  const sender  = results[0]?.sender || '?';
  const certain = results.reduce((s, r) => s + (r.certain || 0), 0);
  const total   = results.reduce((s, r) => s + (r.total || 0), 0);

  return {
    isSIL:   true,
    decoded: fullDecoded,
    intent,
    sender,
    certain,
    total,
    integrity: results.every(r => r.integrity),
    sigOk:     results.every(r => r.sigOk),
    chunks:    results,
  };
}

// ============================================================
// A2A SERVER — minimal implementation for SIL agents
// ============================================================

/**
 * Build an A2A Agent Card for a SIL agent.
 * Published at /.well-known/agent.json
 */
function buildAgentCard(agentId, description, skills = [], endpoint = null) {
  const [name, domain] = agentId.split('@');
  return {
    name:        name,
    description: description,
    version:     '1.0',
    url:         endpoint || `https://${domain}/a2a`,
    provider: {
      organization: domain,
      url:          `https://${domain}`,
    },
    capabilities: {
      streaming:         false,
      pushNotifications: false,
    },
    skills: skills.map(s => ({
      id:          s.id || s.name.toLowerCase().replace(/\s+/g, '-'),
      name:        s.name,
      description: s.description || '',
      tags:        s.tags || [],
    })),
    // SIL extension declaration
    extensions: [{
      uri:     'https://silenceprotocol.org/extensions/sil/1.5',
      version: '1.5',
      params: {
        cipher:       'LKE-6',
        scripts:      ['CU', 'LB', 'LB2', 'CP', 'PM', 'PS'],
        transport:    'fork-sil',
        a2a_compat:   true,
        content_type: 'application/x-sil',
      }
    }],
    security: [{
      type:        'x-sil-hmac',
      description: 'HMAC-SHA256 shared secret. Exchange out-of-band.',
    }],
    metadata: {
      'x-protocol': 'SIL/1.5',
      'x-integrity': 'proof-by-nine',
      'x-repo':     'github.com/zeromail-protocol/silence-protocol',
    }
  };
}

/**
 * Process an incoming A2A message.
 * Returns decoded SIL content or null if not SIL.
 */
function processIncomingA2A(a2aMessage, secret) {
  if (!hasSILParts(a2aMessage)) {
    // Standard A2A message — not encrypted
    const parts = a2aMessage?.params?.message?.parts ||
                  a2aMessage?.message?.parts || [];
    const textParts = parts.filter(p => p.text);
    return {
      isSIL:   false,
      decoded: textParts.map(p => p.text).join(' '),
      intent:  'INFO',
    };
  }
  return decodeFromA2AMessage(a2aMessage, secret);
}

// ============================================================
// A2A HTTP SERVER — minimal for testing
// ============================================================

/**
 * Create a minimal A2A-compatible HTTP server for a SIL agent.
 * Handles:
 *   GET  /.well-known/agent.json  → Agent Card
 *   POST /a2a                      → message/send
 */
function createA2AServer(agentId, secret, agentCard, onMessage) {
  const http = require('http');

  const server = http.createServer((req, res) => {
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

    if (req.method === 'OPTIONS') {
      res.writeHead(200); res.end(); return;
    }

    // Agent Card discovery
    if (req.method === 'GET' && req.url === '/.well-known/agent.json') {
      res.writeHead(200);
      res.end(JSON.stringify(agentCard, null, 2));
      return;
    }

    // A2A endpoint
    if (req.method === 'POST' && (req.url === '/a2a' || req.url === '/')) {
      let body = '';
      req.on('data', d => { body += d; });
      req.on('end', async () => {
        try {
          const a2aMsg = JSON.parse(body);

          if (a2aMsg.method !== 'message/send') {
            res.writeHead(400);
            res.end(JSON.stringify({
              jsonrpc: '2.0', id: a2aMsg.id,
              error: { code: -32601, message: 'Method not found' }
            }));
            return;
          }

          // Decode incoming message (SIL or plaintext)
          const decoded = processIncomingA2A(a2aMsg, secret);

          // Call the agent's handler
          const response = await onMessage(decoded, a2aMsg);

          // Build A2A response
          const taskId  = crypto.randomUUID();
          const a2aResp = {
            jsonrpc: '2.0',
            id:      a2aMsg.id,
            result: {
              id:     taskId,
              status: { state: 'completed' },
              artifacts: response ? [{
                artifactId: crypto.randomUUID(),
                name:       'response',
                parts:      response.parts || [{ text: response.text || '' }],
              }] : [],
            }
          };

          res.writeHead(200);
          res.end(JSON.stringify(a2aResp));

        } catch (e) {
          res.writeHead(500);
          res.end(JSON.stringify({
            jsonrpc: '2.0',
            error: { code: -32603, message: e.message }
          }));
        }
      });
      return;
    }

    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Not found' }));
  });

  return server;
}

module.exports = {
  encodeToA2APart,
  buildA2AMessage,
  hasSILParts,
  decodeFromA2AMessage,
  processIncomingA2A,
  buildAgentCard,
  createA2AServer,
  SIL_MEDIA_TYPE,
  SIL_VERSION,
};
