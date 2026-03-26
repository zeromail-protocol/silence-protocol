#!/usr/bin/env node
/**
 * SIL A2A Bridge — End-to-End Test
 * Tests: encode/decode via A2A, agent card, HTTP server
 *
 * Usage: node examples/test_a2a.js
 */

const {
  buildA2AMessage,
  decodeFromA2AMessage,
  buildAgentCard,
  createA2AServer,
  encodeToA2APart,
  hasSILParts,
} = require('../lib/a2a_bridge');
const http = require('http');

const SECRET  = 'scorent-noctia-test-2026';
const SENDER  = 'karine@scorent';
const RECIP   = 'salomon@noctia';
const MESSAGE = 'SCORE 745 REVENUS 4200 INCIDENTS 0';

let passed = 0, failed = 0;

function assert(label, condition) {
  if (condition) { console.log(`  \x1b[32m✓\x1b[0m ${label}`); passed++; }
  else           { console.log(`  \x1b[31m✗\x1b[0m ${label}`); failed++; }
}

async function run() {
  console.log('\n\x1b[1m═══ A2A BRIDGE END-TO-END TEST ═══\x1b[0m\n');

  // ── Test 1: Build A2A message ──
  console.log('\x1b[33m[1] Build A2A Message\x1b[0m');
  const a2aMsg = buildA2AMessage(MESSAGE, SECRET, SENDER, RECIP, 'REQUEST');
  assert('JSON-RPC 2.0 format',    a2aMsg.jsonrpc === '2.0');
  assert('Method is message/send',  a2aMsg.method === 'message/send');
  assert('Has SIL parts',           a2aMsg.params.message.parts.length > 0);
  assert('MediaType is x-sil',      a2aMsg.params.message.parts[0].mediaType === 'application/x-sil');
  assert('Has signature',           a2aMsg.params.message.parts[0].data['x-sil-signature'].length === 64);

  // ── Test 2: Decode A2A message ──
  console.log('\n\x1b[33m[2] Decode A2A Message\x1b[0m');
  const dec = decodeFromA2AMessage(a2aMsg, SECRET);
  assert('Decoded matches original', dec.decoded === MESSAGE);
  assert('Signature valid',          dec.sigOk);
  assert('100% certainty',           dec.certain === dec.total);
  assert('Integrity OK',             dec.integrity);
  console.log(`  Decoded: "${dec.decoded}" (${dec.certain}/${dec.total})`);

  // ── Test 3: Agent Card ──
  console.log('\n\x1b[33m[3] Agent Card\x1b[0m');
  const card = buildAgentCard(SENDER, 'Scoring immobilier', [
    { name: 'Tenant Scoring', description: 'Score locataire', tags: ['scoring'] },
  ], 'http://localhost:3333/a2a');
  assert('Card name is karine',    card.name === 'karine');
  assert('Card has SIL extension', card.extensions[0].uri.includes('sil'));
  assert('Card has skills',        card.skills.length === 1);

  // ── Test 4: A2A HTTP Server ──
  console.log('\n\x1b[33m[4] A2A HTTP Server\x1b[0m');
  const server = createA2AServer(RECIP, SECRET, card, async (decoded) => {
    return { parts: encodeToA2APart(`RECU ${decoded.decoded}`, SECRET, RECIP, 'INFO') };
  });

  await new Promise(resolve => server.listen(3333, resolve));

  // Agent Card endpoint
  const cardRes = JSON.parse(await httpGet('http://localhost:3333/.well-known/agent.json'));
  assert('GET agent.json works', cardRes.name === 'karine');

  // Send SIL message
  const testMsg = buildA2AMessage('SOLDE RIVOLI', SECRET, SENDER, RECIP, 'REQUEST');
  const resp = JSON.parse(await httpPost('http://localhost:3333/a2a', testMsg));
  assert('Task completed',       resp.result?.status?.state === 'completed');
  assert('Has SIL response',     resp.result?.artifacts?.[0]?.parts?.some(p => p.mediaType === 'application/x-sil'));

  // Decode response
  const respParts = resp.result?.artifacts?.[0]?.parts || [];
  const respDec = decodeFromA2AMessage({ params: { message: { parts: respParts } } }, SECRET);
  assert('Response decoded OK',  respDec.decoded.startsWith('RECU'));
  assert('Response 100% certain', respDec.certain === respDec.total);
  console.log(`  Server response: "${respDec.decoded}"`);

  server.close();
  console.log(`\n\x1b[1m═══ RESULTS: ${passed} passed, ${failed} failed ═══\x1b[0m\n`);
  process.exit(failed > 0 ? 1 : 0);
}

function httpGet(url) {
  return new Promise((resolve, reject) => {
    http.get(url, res => { let d = ''; res.on('data', c => d += c); res.on('end', () => resolve(d)); }).on('error', reject);
  });
}
function httpPost(url, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const u = new URL(url);
    const req = http.request({ hostname: u.hostname, port: u.port, path: u.pathname, method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) }
    }, res => { let d = ''; res.on('data', c => d += c); res.on('end', () => resolve(d)); });
    req.on('error', reject);
    req.write(data); req.end();
  });
}

run().catch(e => { console.error(e); process.exit(1); });
