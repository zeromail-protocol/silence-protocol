/**
 * SIL SDK — Silence Protocol v1.6
 * Content-encrypted agent-to-agent communication
 * A2A confidentiality layer
 */

const { encode, decode, decodeChunk, ALPHABETS } = require('./cipher');
const fs     = require('fs');
const path   = require('path');
const crypto = require('crypto');

const CONFIG_FILE = '.sil-config';
const INBOX_DIR   = 'sil_inbox';
const DONE_FILE   = '.sil-processed';

function loadConfig(dir = process.cwd()) {
  const p = path.join(dir, CONFIG_FILE);
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

function saveConfig(config, dir = process.cwd()) {
  fs.writeFileSync(path.join(dir, CONFIG_FILE), JSON.stringify(config, null, 2));
}

function send(message, intent = 'INFO', config, dir = process.cwd()) {
  const { agent_id, recipient_id, shared_secret } = config;
  const enc_chunks = encode(message, shared_secret);
  const filepaths = [];

  enc_chunks.forEach((chunk) => {
    const msgId = crypto.createHash('sha256')
      .update(`${agent_id}${message}${Date.now()}${chunk.chunkIndex}`)
      .digest('hex').slice(0, 16);

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const suffix = enc_chunks.length > 1 ? `_c${chunk.chunkIndex + 1}of${enc_chunks.length}` : '';
    const filename = `${timestamp}_${msgId}${suffix}_${intent}.sil`;

    const silContent = {
      header: {
        sil_version: '1.6', message_id: msgId,
        sender: agent_id, recipient: recipient_id,
        sent_at: new Date().toISOString(), intent,
        'x-sil-nonce': chunk.nonce,
        scripts_used: chunk.langsUsed, gkl_checksum: chunk.gklGlobal,
        chunk_index: chunk.chunkIndex, total_chunks: enc_chunks.length
      },
      encoded: chunk.encoded,
      signature: crypto.createHash('sha256')
        .update(`${shared_secret}${chunk.encoded}`).digest('hex')
    };

    const inbox = path.join(dir, INBOX_DIR, `from_${agent_id.split('@')[0]}`);
    fs.mkdirSync(inbox, { recursive: true });
    const filepath = path.join(inbox, filename);
    fs.writeFileSync(filepath, JSON.stringify(silContent, null, 2), 'utf8');
    filepaths.push(filepath);
  });

  return { filepaths, enc_chunks };
}

function receive(config, dir = process.cwd()) {
  const { shared_secret, agent_id } = config;
  const processed = new Set(
    fs.existsSync(path.join(dir, DONE_FILE))
      ? fs.readFileSync(path.join(dir, DONE_FILE), 'utf8').split('\n').filter(Boolean)
      : []
  );

  const inboxDir = path.join(dir, INBOX_DIR);
  if (!fs.existsSync(inboxDir)) return [];

  const files = [];
  const walk = d => {
    for (const f of fs.readdirSync(d)) {
      const full = path.join(d, f);
      if (fs.statSync(full).isDirectory()) walk(full);
      else if (f.endsWith('.sil') && !processed.has(full)) files.push(full);
    }
  };
  walk(inboxDir);

  const messages = [];
  for (const filepath of files.sort()) {
    try {
      const sil = JSON.parse(fs.readFileSync(filepath, 'utf8'));
      const { header, encoded, signature } = sil;
      if (header.sender === agent_id) {
        fs.appendFileSync(path.join(dir, DONE_FILE), filepath + '\n');
        continue;
      }
      const expectedSig = crypto.createHash('sha256')
        .update(`${shared_secret}${encoded}`).digest('hex');
      const sigOk = signature === expectedSig;
      if (!sigOk) {
        messages.push({ filepath, error: 'INVALID_SIGNATURE', header });
        fs.appendFileSync(path.join(dir, DONE_FILE), filepath + '\n');
        continue;
      }
      const chunkIndex = header.chunk_index || 0;
      const nonce = header['x-sil-nonce'] || '';
      const dec = decodeChunk(encoded, shared_secret, chunkIndex, nonce);
      messages.push({ filepath, header, encoded, decoded: dec.decoded, certain: dec.certain, total: dec.total, integrity: dec.integrity, sigOk });
      fs.appendFileSync(path.join(dir, DONE_FILE), filepath + '\n');
    } catch (e) {
      messages.push({ filepath, error: e.message });
    }
  }
  return messages;
}

async function init(options) {
  const { agentId, recipientId, secret, dir = process.cwd() } = options;
  fs.mkdirSync(path.join(dir, INBOX_DIR), { recursive: true });
  const config = { agent_id: agentId, recipient_id: recipientId, shared_secret: secret, sil_version: '1.6', created_at: new Date().toISOString() };
  saveConfig(config, dir);
  return config;
}

module.exports = { encode, decode, decodeChunk, send, receive, init, loadConfig, saveConfig, ALPHABETS };
