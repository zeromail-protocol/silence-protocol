#!/usr/bin/env node
/**
 * SIL Group Protocol — End-to-End Broadcast Test
 *
 * Tests multicast encrypted messaging with 3 agents in one group.
 * Usage: node examples/test_group_broadcast.js
 */

const { createGroup, joinGroup, sendGroup, receiveGroup, listGroups } = require('../lib/group');
const { decode } = require('../lib/cipher');
const os   = require('os');
const path = require('path');
const fs   = require('fs');

const GROUP_ID     = 'RIVOLI_PROJECT';
const GROUP_SECRET = 'group-rivoli-secret-2026';
const WRONG_SECRET = 'wrong-secret-intruder';

const SALOMON = 'salomon@noctia';
const KARINE  = 'karine@scorent';
const FISCAL  = 'fiscal@fiscalready';

let passed = 0, failed = 0;

function assert(label, condition) {
  if (condition) { console.log(`  \x1b[32m✓\x1b[0m ${label}`); passed++; }
  else           { console.log(`  \x1b[31m✗\x1b[0m ${label}`); failed++; }
}

// Create temp dirs for each agent
const tmpBase  = path.join(os.tmpdir(), `sil-group-test-${Date.now()}`);
const dirS     = path.join(tmpBase, 'salomon');
const dirK     = path.join(tmpBase, 'karine');
const dirF     = path.join(tmpBase, 'fiscal');
[dirS, dirK, dirF].forEach(d => fs.mkdirSync(d, { recursive: true }));

function copyGroupMessages(fromDir, toDir) {
  const src = path.join(fromDir, 'sil_inbox', 'groups', GROUP_ID);
  const dst = path.join(toDir, 'sil_inbox', 'groups', GROUP_ID);
  if (!fs.existsSync(src)) return;
  fs.mkdirSync(dst, { recursive: true });
  for (const f of fs.readdirSync(src).filter(f => f.endsWith('.sil'))) {
    fs.copyFileSync(path.join(src, f), path.join(dst, f));
  }
}

function run() {
  console.log('\n\x1b[1m═══ SIL GROUP PROTOCOL — BROADCAST TEST ═══\x1b[0m\n');

  // ── Step 1: Create group ──
  console.log('\x1b[33m[1] Create Group\x1b[0m');
  const grp = createGroup(GROUP_ID, [SALOMON, KARINE, FISCAL], GROUP_SECRET, SALOMON);
  assert('Group created', grp.group_id === GROUP_ID);
  assert('Has 3 members', grp.members.length === 3);
  assert('Creator is Salomon', grp.creator === SALOMON);
  assert('Protocol is SIL-Group/1.0', grp.protocol === 'SIL-Group/1.0');
  console.log(`  Group: ${grp.group_id} — ${grp.members.join(', ')}`);

  // ── Step 2: All agents join ──
  console.log('\n\x1b[33m[2] Agents Join Group\x1b[0m');
  joinGroup(GROUP_ID, SALOMON, GROUP_SECRET, grp.members, dirS);
  joinGroup(GROUP_ID, KARINE,  GROUP_SECRET, grp.members, dirK);
  joinGroup(GROUP_ID, FISCAL,  GROUP_SECRET, grp.members, dirF);
  assert('Salomon joined', listGroups(dirS).length === 1);
  assert('Karine joined',  listGroups(dirK).length === 1);
  assert('Fiscal joined',  listGroups(dirF).length === 1);

  // ── Step 3: Salomon sends group message ──
  console.log('\n\x1b[33m[3] Salomon Sends Group Message\x1b[0m');
  const msg1 = 'REUNION DOSSIER RIVOLI DEMAIN 14H';
  const sent1 = sendGroup(msg1, 'INFO', GROUP_ID, SALOMON, GROUP_SECRET, dirS);
  assert('Message file created', sent1.filepaths.length === 1);
  assert('Tokens encoded', sent1.enc_chunks[0].results.length === msg1.length);
  console.log(`  Encoded: ${sent1.enc_chunks[0].encoded.slice(0, 50)}...`);
  console.log(`  Tokens: ${sent1.enc_chunks[0].results.length}`);

  // Copy to all agents' inboxes (simulating transport)
  copyGroupMessages(dirS, dirK);
  copyGroupMessages(dirS, dirF);

  // ── Step 4: Karine receives and decodes ──
  console.log('\n\x1b[33m[4] Karine Receives\x1b[0m');
  const karineRcv = receiveGroup(GROUP_ID, KARINE, GROUP_SECRET, dirK);
  assert('Karine got 1 message', karineRcv.length === 1);
  assert('Decoded matches',      karineRcv[0].decoded === msg1);
  assert('100% certain',         karineRcv[0].certain === karineRcv[0].total);
  assert('Signature valid',      karineRcv[0].sigOk);
  assert('Sender is Salomon',    karineRcv[0].sender === SALOMON);
  console.log(`  Decoded: "${karineRcv[0].decoded}" (${karineRcv[0].certain}/${karineRcv[0].total})`);

  // ── Step 5: Fiscal receives and decodes ──
  console.log('\n\x1b[33m[5] Fiscal Receives\x1b[0m');
  const fiscalRcv = receiveGroup(GROUP_ID, FISCAL, GROUP_SECRET, dirF);
  assert('Fiscal got 1 message', fiscalRcv.length === 1);
  assert('Decoded matches',      fiscalRcv[0].decoded === msg1);
  assert('100% certain',         fiscalRcv[0].certain === fiscalRcv[0].total);
  assert('Signature valid',      fiscalRcv[0].sigOk);
  assert('Sender is Salomon',    fiscalRcv[0].sender === SALOMON);
  console.log(`  Decoded: "${fiscalRcv[0].decoded}" (${fiscalRcv[0].certain}/${fiscalRcv[0].total})`);

  // ── Step 6: Karine replies to group ──
  console.log('\n\x1b[33m[6] Karine Replies to Group\x1b[0m');
  const msg2 = 'CONFIRME SCORE PRET';
  const sent2 = sendGroup(msg2, 'INFO', GROUP_ID, KARINE, GROUP_SECRET, dirK);
  assert('Karine reply sent', sent2.filepaths.length === 1);
  console.log(`  Message: "${msg2}"`);

  // ── Step 7: Fiscal replies to group ──
  console.log('\n\x1b[33m[7] Fiscal Replies to Group\x1b[0m');
  const msg3 = 'CONFIRME ANALYSE FISCALE PRETE';
  const sent3 = sendGroup(msg3, 'INFO', GROUP_ID, FISCAL, GROUP_SECRET, dirF);
  assert('Fiscal reply sent', sent3.filepaths.length === 1);
  console.log(`  Message: "${msg3}"`);

  // Copy replies to Salomon
  copyGroupMessages(dirK, dirS);
  copyGroupMessages(dirF, dirS);

  // ── Step 8: Salomon receives both replies ──
  console.log('\n\x1b[33m[8] Salomon Receives Replies\x1b[0m');
  const salomonRcv = receiveGroup(GROUP_ID, SALOMON, GROUP_SECRET, dirS);
  assert('Salomon got 2 messages', salomonRcv.length === 2);

  const fromKarine = salomonRcv.find(m => m.sender === KARINE);
  const fromFiscal = salomonRcv.find(m => m.sender === FISCAL);

  assert('Karine reply decoded',  fromKarine?.decoded === msg2);
  assert('Karine 100% certain',   fromKarine?.certain === fromKarine?.total);
  assert('Karine sig valid',      fromKarine?.sigOk);
  assert('Fiscal reply decoded',  fromFiscal?.decoded === msg3);
  assert('Fiscal 100% certain',   fromFiscal?.certain === fromFiscal?.total);
  assert('Fiscal sig valid',      fromFiscal?.sigOk);

  console.log(`  From Karine: "${fromKarine?.decoded}" (${fromKarine?.certain}/${fromKarine?.total})`);
  console.log(`  From Fiscal: "${fromFiscal?.decoded}" (${fromFiscal?.certain}/${fromFiscal?.total})`);

  // ── Step 9: Cross-secret isolation ──
  console.log('\n\x1b[33m[9] Cross-Secret Isolation\x1b[0m');

  // Try decoding with wrong secret
  const wrongDec = decode(sent1.enc_chunks[0].encoded, WRONG_SECRET);
  assert('Wrong secret = garbage', wrongDec.decoded !== msg1);
  console.log(`  Wrong key decode: "${wrongDec.decoded.slice(0, 30)}..." (garbage)`);

  // Try receiving with wrong secret
  // Copy Salomon's original message to a temp dir and try wrong secret
  const dirIntruder = path.join(tmpBase, 'intruder');
  fs.mkdirSync(dirIntruder, { recursive: true });
  joinGroup(GROUP_ID, 'intruder@evil', WRONG_SECRET, [], dirIntruder);
  copyGroupMessages(dirS, dirIntruder);
  const intruderRcv = receiveGroup(GROUP_ID, 'intruder@evil', WRONG_SECRET, dirIntruder);
  const intruderSigFail = intruderRcv.every(m => m.error === 'INVALID_SIGNATURE' || m.decoded !== msg1);
  assert('Intruder cannot decode', intruderSigFail);

  // ── Step 10: No duplicate reads ──
  console.log('\n\x1b[33m[10] Idempotent Receive\x1b[0m');
  const karineAgain = receiveGroup(GROUP_ID, KARINE, GROUP_SECRET, dirK);
  assert('Re-read returns 0 (already processed)', karineAgain.length === 0);

  // ── Cleanup ──
  fs.rmSync(tmpBase, { recursive: true, force: true });

  // ── Summary ──
  console.log(`\n\x1b[1m═══ RESULTS: ${passed} passed, ${failed} failed ═══\x1b[0m`);
  console.log(`  Group: ${GROUP_ID} — 3 members`);
  console.log(`  Messages: 3 sent, 3 received, all 100% certain`);
  console.log(`  Cross-secret isolation: verified`);
  console.log(`  Idempotent receive: verified\n`);

  process.exit(failed > 0 ? 1 : 0);
}

run();
