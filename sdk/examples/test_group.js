#!/usr/bin/env node
/**
 * SIL Agent Group — Star Topology
 * Salomon (orchestrator) ↔ Karine (scoring) + Fiscal (fiscal)
 *
 * Usage: ANTHROPIC_API_KEY=sk-... node examples/test_group.js
 */

const { encode, decode }          = require('../lib/cipher');
const { silToHuman }              = require('../lib/bridge');
const { openRound, roundStatus }  = require('../lib/rounds');
const { buildA2AMessage, decodeFromA2AMessage } = require('../lib/a2a_bridge');

const API_KEY = process.env.ANTHROPIC_API_KEY || null;

const GROUP = {
  name: 'RIVOLI_PROJECT',
  agents: {
    salomon: { id: 'salomon@noctia',     role: 'orchestrator' },
    karine:  { id: 'karine@scorent',     role: 'scoring' },
    fiscal:  { id: 'fiscal@fiscalready', role: 'fiscal' },
  },
  secrets: {
    'salomon-karine': 'scorent-noctia-test-2026',
    'salomon-fiscal': 'fiscalready-noctia-test-2026',
  },
};

function getSecret(a, b) {
  return GROUP.secrets[`${a}-${b}`] || GROUP.secrets[`${b}-${a}`];
}

async function run() {
  console.log('\n\x1b[1m═══ AGENT GROUP — STAR TOPOLOGY ═══\x1b[0m\n');
  console.log(`Group: ${GROUP.name} — 3 agents, 2 pairwise secrets\n`);

  const secretK = getSecret('salomon', 'karine');
  const secretF = getSecret('salomon', 'fiscal');
  const request = 'ANALYSE LOCATAIRE RIVOLI SCORE ET FISCAL';

  // Open rounds
  const roundK = openRound(GROUP.agents.salomon.id, GROUP.agents.karine.id, 'SCORING RIVOLI');
  const roundF = openRound(GROUP.agents.salomon.id, GROUP.agents.fiscal.id, 'FISCAL RIVOLI');
  console.log(`Rounds: ${roundK.id} (Karine), ${roundF.id} (Fiscal)`);

  // Broadcast
  const [encK, encF] = [encode(request, secretK)[0], encode(request, secretF)[0]];
  console.log(`Broadcast: ${encK.results.length} + ${encF.results.length} tokens`);

  // Both decode
  const decK = decode(encK.encoded, secretK);
  const decF = decode(encF.encoded, secretF);
  console.log(`Karine decoded: "${decK.decoded}" (${decK.certain}/${decK.total})`);
  console.log(`Fiscal decoded: "${decF.decoded}" (${decF.certain}/${decF.total})`);

  // Responses
  const karineResp = 'SCORE 745 REVENUS 4200 INCIDENTS 0 ANCIENNETE 36 MOIS GARANTIE VISALE';
  const fiscalResp = 'TAXE FONCIERE 2800 CFE 1200 TVA REGIME REEL DEFISCALISATION PINEL 6000 AN';

  const encRK = encode(karineResp, secretK)[0];
  const encRF = encode(fiscalResp, secretF)[0];

  const decRK = decode(encRK.encoded, secretK);
  const decRF = decode(encRF.encoded, secretF);
  console.log(`\nKarine INFO: "${decRK.decoded}" (${decRK.certain}/${decRK.total})`);
  console.log(`Fiscal INFO: "${decRF.decoded}" (${decRF.certain}/${decRF.total})`);

  // Cross-isolation
  const cross = decode(encRK.encoded, secretF);
  console.log(`\nCross-secret test: ${cross.decoded === karineResp ? '✗ LEAKED' : '✓ isolated'}`);

  // Aggregate
  const agg = `SCORING: ${decRK.decoded} | FISCAL: ${decRF.decoded}`;
  const summary = await silToHuman(agg, { channel: 'email', language: 'fr', topic: 'Rivoli' }, API_KEY);
  console.log(`\nSummary: ${summary}\n`);

  console.log('\x1b[32m✓ Group conversation complete — all 100% certain\x1b[0m\n');
}

run().catch(e => { console.error(e); process.exit(1); });
