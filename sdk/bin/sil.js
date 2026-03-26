#!/usr/bin/env node
/**
 * SIL CLI v1.5 — Silence Protocol
 * npm install -g @silence-protocol/sil
 */

const { program } = require('commander');
const inquirer    = require('inquirer');
const { execSync } = require('child_process');
const path = require('path');
const fs   = require('fs');
const { encode, decode, send, receive, init, loadConfig, ALPHABETS } = require('../lib/index');
const { createGroup, joinGroup, loadGroup, listGroups, sendGroup, receiveGroup } = require('../lib/group');

const G = '\x1b[33m', R = '\x1b[0m', B = '\x1b[1m', M = '\x1b[90m', GR = '\x1b[32m';

function box(title, lines) {
  const w = 58;
  console.log(`\n${G}┌${'─'.repeat(w)}┐${R}`);
  console.log(`${G}│${R} ${B}${title.padEnd(w - 1)}${R}${G}│${R}`);
  console.log(`${G}├${'─'.repeat(w)}┤${R}`);
  for (const l of lines) console.log(`${G}│${R} ${l.padEnd(w - 1)}${G}│${R}`);
  console.log(`${G}└${'─'.repeat(w)}┘${R}\n`);
}

// ─── sil init ───────────────────────────────────────────────
program.command('init')
  .description('Initialize a SIL canal between two agents')
  .option('--agent <id>')
  .option('--recipient <id>')
  .option('--secret <secret>')
  .action(async (opts) => {
    console.log(`\n${G}${B}SIL — Silence Protocol v1.5${R}`);
    console.log(`${M}Content-encrypted agent-to-agent communication${R}\n`);

    const answers = await inquirer.default.prompt([
      { type: 'input',    name: 'agentId',     message: 'Agent ID (e.g. karine@scorent):', when: !opts.agent },
      { type: 'input',    name: 'recipientId', message: 'Recipient ID:', when: !opts.recipient },
      { type: 'password', name: 'secret',      message: 'Shared secret (same on both sides):', when: !opts.secret },
    ]);

    const agentId     = opts.agent     || answers.agentId;
    const recipientId = opts.recipient || answers.recipientId;
    const secret      = opts.secret    || answers.secret;

    await init({ agentId, recipientId, secret });

    box('✓ SIL Canal Initialized', [
      `Agent     : ${agentId}`,
      `Recipient : ${recipientId}`,
      `Secret    : ${'•'.repeat(secret.length)}`,
      `Version   : SIL v1.5 — 6 ancient scripts`,
      '',
      'Send    : sil send "YOUR MESSAGE" --intent REQUEST',
      'Receive : sil receive',
      'Status  : sil status',
    ]);
  });

// ─── sil send ───────────────────────────────────────────────
program.command('send <message>')
  .description('Send a SIL-encrypted message')
  .option('--intent <intent>', 'OFFER|REQUEST|INFO|ALERT|NEGOTIATION', 'INFO')
  .option('--push', 'git push after sending')
  .action((message, opts) => {
    const config = loadConfig();
    if (!config) { console.error(`${R}✗ No config. Run: sil init`); process.exit(1); }

    const { filepaths, enc_chunks } = send(message, opts.intent, config);
    const enc = enc_chunks[0];
    const scriptNames = enc.langsUsed.map(l => ALPHABETS[l].name);

    box('SIL — MESSAGE SENT', [
      `From    : ${config.agent_id}`,
      `To      : ${config.recipient_id}`,
      `Intent  : ${opts.intent}`,
      `Message : ${message}`,
      '',
      `Encoded : ${enc.encoded.slice(0, 40)}...`,
      `Scripts : ${scriptNames.join(' · ')}`,
      `Chunks  : ${enc_chunks.length}`,
      `GKL     : ${enc.gklGlobal}`,
      '',
      `File    : ${path.basename(filepaths[0])}`,
    ]);

    console.log(`${M}Token  Script              Symbols    9?${R}`);
    console.log(`${M}${'─'.repeat(45)}${R}`);
    for (const r of enc.results.slice(0, 12)) {
      const ok = r.ok ? `${GR}✓${R}` : `\x1b[31m✗${R}`;
      console.log(`${r.token.padEnd(6)} ${r.langName.padEnd(20)} ${r.symbols.padEnd(10)} ${ok}`);
    }
    if (enc.results.length > 12) console.log(`${M}... +${enc.results.length - 12} more tokens${R}`);

    if (opts.push) {
      try {
        execSync('git add . && git commit -m "SIL ' + opts.intent + ' ' + config.agent_id + '" && git push', { stdio: 'inherit' });
        console.log(`\n${GR}✓ Pushed to Git${R}`);
      } catch (e) {
        console.log(`\n${M}⚠ Push failed — run git push manually${R}`);
      }
    } else {
      console.log(`\n${M}→ To send via Git: sil send "..." --push${R}`);
    }
  });

// ─── sil receive ────────────────────────────────────────────
program.command('receive')
  .description('Receive and decode SIL messages')
  .option('--pull', 'git pull before reading')
  .action((opts) => {
    const config = loadConfig();
    if (!config) { console.error('✗ No config. Run: sil init'); process.exit(1); }

    if (opts.pull) {
      try { execSync('git pull', { stdio: 'inherit' }); } catch (e) {}
    }

    const messages = receive(config);
    if (!messages.length) {
      console.log(`\n${M}SIL — No new messages.${R}\n`);
      return;
    }

    console.log(`\n${G}${B}SIL — ${messages.length} NEW MESSAGE(S)${R}\n`);

    for (const msg of messages) {
      if (msg.error) {
        console.log(`\x1b[31m✗ ${msg.filepath}: ${msg.error}${R}\n`);
        continue;
      }
      const { header, decoded, certain, total, sigOk } = msg;
      const scriptNames = (header.scripts_used || []).map(l => ALPHABETS[l]?.name || l);
      box(`✓ ${header.intent} — ${header.sender}`, [
        `From      : ${header.sender}`,
        `To        : ${header.recipient}`,
        `Intent    : ${header.intent}`,
        `Sent      : ${header.sent_at}`,
        `Scripts   : ${scriptNames.join(' · ')}`,
        '',
        `Signature : ${sigOk ? '✓ valid' : '✗ INVALID'}`,
        `Decoded   : ${decoded}`,
        `Certain   : ${certain}/${total} tokens`,
      ]);
    }
  });

// ─── sil status ─────────────────────────────────────────────
program.command('status')
  .description('Show canal status')
  .action(() => {
    const config = loadConfig();
    if (!config) { console.log(`\n${M}No canal configured. Run: sil init${R}\n`); return; }

    let msgCount = 0;
    const inboxDir = path.join(process.cwd(), 'sil_inbox');
    if (fs.existsSync(inboxDir)) {
      const walk = d => { for (const f of fs.readdirSync(d)) { const full = path.join(d, f); if (fs.statSync(full).isDirectory()) walk(full); else if (f.endsWith('.sil')) msgCount++; } };
      walk(inboxDir);
    }

    box('SIL — Status', [
      `Agent     : ${config.agent_id}`,
      `Recipient : ${config.recipient_id}`,
      `Version   : SIL v${config.sil_version}`,
      `Messages  : ${msgCount} file(s) in inbox`,
      '',
      `Cipher    : v1.5 — 6 scripts >= 45 symbols`,
      `Scripts   : CU · LB · LB2 · CP · PM · PS`,
      `Chunking  : 200 tokens/chunk`,
      '',
      `HIRAM     : \u{10914}\u{10914}\u{12000}\u{1207F}\u{12103}\u{12023}\u{10906}\u{1090D}\u{12001}\u{12078}`,
      `\u05D0\u05DE\u05EA = GKL(441) = 9`,
    ]);
  });

// ─── sil encode / decode ────────────────────────────────────
program.command('encode <message>')
  .option('--secret <secret>')
  .action((message, opts) => {
    const config = loadConfig();
    const secret = opts.secret || config?.shared_secret || 'sil-demo-2026';
    const chunks = encode(message, secret);
    const enc = chunks[0];
    console.log(`\n${B}Original${R} : ${message}`);
    console.log(`${B}Encoded ${R} : ${enc.encoded}`);
    console.log(`${B}Scripts ${R} : ${enc.langsUsed.map(l => ALPHABETS[l].name).join(' · ')}`);
    console.log(`${B}Chunks  ${R} : ${chunks.length}`);
    console.log(`${B}GKL     ${R} : ${enc.gklGlobal}\n`);
  });

program.command('decode <encoded>')
  .option('--secret <secret>')
  .option('--chunk <n>', 'chunk index', '0')
  .action((encoded, opts) => {
    const config = loadConfig();
    const secret = opts.secret || config?.shared_secret || 'sil-demo-2026';
    const dec = decode(encoded, secret, parseInt(opts.chunk));
    console.log(`\n${B}Encoded ${R} : ${encoded.slice(0, 40)}...`);
    console.log(`${B}Decoded ${R} : ${dec.decoded}`);
    console.log(`${B}Certain ${R} : ${dec.certain}/${dec.total}`);
    console.log(`${B}Integrity${R}: ${dec.integrity ? `${GR}✓${R}` : '\x1b[31m✗\x1b[0m'}\n`);
  });

// ─── sil group ────────────────────────────────────────────
const group = program.command('group').description('SIL Group Protocol — multicast encrypted messaging');

group.command('create')
  .description('Create a new SIL group')
  .requiredOption('--id <groupId>', 'Group identifier')
  .requiredOption('--members <members>', 'Comma-separated agent IDs')
  .requiredOption('--secret <secret>', 'Group shared secret')
  .action((opts) => {
    const config = loadConfig();
    const agentId = config?.agent_id || opts.members.split(',')[0].trim();
    const members = opts.members.split(',').map(m => m.trim());
    const grp = createGroup(opts.id, members, opts.secret, agentId);
    joinGroup(opts.id, agentId, opts.secret, members);
    box('✓ SIL Group Created', [
      `Group   : ${opts.id}`,
      `Members : ${members.join(', ')}`,
      `Secret  : ${'•'.repeat(opts.secret.length)}`,
      `Creator : ${agentId}`,
      '',
      `Send    : sil group send "MSG" --group ${opts.id}`,
      `Receive : sil group receive --group ${opts.id}`,
    ]);
  });

group.command('join')
  .description('Join an existing SIL group')
  .requiredOption('--id <groupId>', 'Group identifier')
  .requiredOption('--secret <secret>', 'Group shared secret')
  .action((opts) => {
    const config = loadConfig();
    if (!config) { console.error('✗ No config. Run: sil init first'); process.exit(1); }
    joinGroup(opts.id, config.agent_id, opts.secret);
    box('✓ Joined SIL Group', [
      `Group : ${opts.id}`,
      `Agent : ${config.agent_id}`,
    ]);
  });

group.command('send <message>')
  .description('Send a message to a SIL group')
  .requiredOption('--group <groupId>', 'Group identifier')
  .option('--intent <intent>', 'OFFER|REQUEST|INFO|ALERT', 'INFO')
  .action((message, opts) => {
    const grp = loadGroup(opts.group);
    if (!grp) { console.error(`✗ Group "${opts.group}" not found. Run: sil group join`); process.exit(1); }
    const { filepaths, enc_chunks } = sendGroup(message, opts.intent, opts.group, grp.agent_id, grp.group_secret);
    const enc = enc_chunks[0];
    const scriptNames = enc.langsUsed.map(l => ALPHABETS[l].name);
    box('SIL — GROUP MESSAGE SENT', [
      `Group   : ${opts.group}`,
      `From    : ${grp.agent_id}`,
      `Intent  : ${opts.intent}`,
      `Message : ${message}`,
      '',
      `Encoded : ${enc.encoded.slice(0, 40)}...`,
      `Scripts : ${scriptNames.join(' · ')}`,
      `Tokens  : ${enc.results.length}`,
      `GKL     : ${enc.gklGlobal}`,
    ]);
  });

group.command('receive')
  .description('Receive messages from a SIL group')
  .requiredOption('--group <groupId>', 'Group identifier')
  .action((opts) => {
    const grp = loadGroup(opts.group);
    if (!grp) { console.error(`✗ Group "${opts.group}" not found.`); process.exit(1); }
    const messages = receiveGroup(opts.group, grp.agent_id, grp.group_secret);
    if (!messages.length) {
      console.log(`\n${M}SIL Group "${opts.group}" — No new messages.${R}\n`);
      return;
    }
    console.log(`\n${G}${B}SIL Group "${opts.group}" — ${messages.length} NEW MESSAGE(S)${R}\n`);
    for (const msg of messages) {
      if (msg.error) { console.log(`\x1b[31m✗ ${msg.error}${R}\n`); continue; }
      const scriptNames = (msg.header.scripts_used || []).map(l => ALPHABETS[l]?.name || l);
      box(`✓ ${msg.intent} — ${msg.sender}`, [
        `Group     : ${msg.groupId}`,
        `From      : ${msg.sender}`,
        `Intent    : ${msg.intent}`,
        `Scripts   : ${scriptNames.join(' · ')}`,
        '',
        `Signature : ${msg.sigOk ? '✓ valid' : '✗ INVALID'}`,
        `Decoded   : ${msg.decoded}`,
        `Certain   : ${msg.certain}/${msg.total} tokens`,
      ]);
    }
  });

group.command('list')
  .description('List all groups')
  .action(() => {
    const groups = listGroups();
    if (!groups.length) { console.log(`\n${M}No groups. Run: sil group create${R}\n`); return; }
    console.log(`\n${G}${B}SIL — ${groups.length} GROUP(S)${R}\n`);
    for (const g of groups) {
      console.log(`  ${B}${g.group_id}${R} — ${g.agent_id} — joined ${g.joined_at?.slice(0, 10) || '?'}`);
      if (g.members?.length) console.log(`  ${M}Members: ${g.members.join(', ')}${R}`);
    }
    console.log();
  });

program.name('sil').description('Silence Protocol — Content-encrypted agent communication').version('1.5.2');
program.parse();
