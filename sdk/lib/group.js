/**
 * SIL Group Protocol v1.0
 *
 * Multicast encrypted messaging — one message, N recipients.
 *
 * Instead of N bilateral channels, a SIL group has:
 * - One group ID (e.g. "RIVOLI_PROJECT")
 * - One group secret shared by all members
 * - One encoded message readable by all members
 * - A group manifest listing members and their agent IDs
 */

const crypto = require('crypto');
const fs     = require('fs');
const path   = require('path');
const { encode, decodeChunk, ALPHABETS } = require('./cipher');

const GROUPS_DIR  = '.sil-groups';
const INBOX_DIR   = 'sil_inbox';
const DONE_FILE   = '.sil-group-processed';

// ============================================================
// GROUP MANAGEMENT
// ============================================================

/**
 * Create a group config.
 * @param {string}   groupId      — unique group identifier
 * @param {string[]} members      — array of agent IDs
 * @param {string}   groupSecret  — shared secret for all members
 * @param {string}   creator      — agent ID of the creator
 * @returns {object} group config
 */
function createGroup(groupId, members, groupSecret, creator = null) {
  return {
    group_id:     groupId,
    members,
    group_secret: groupSecret,
    creator:      creator || members[0],
    created_at:   new Date().toISOString(),
    sil_version:  '1.6',
    protocol:     'SIL-Group/1.0',
  };
}

/**
 * Join a group — saves group config locally.
 * @param {string} groupId     — group identifier
 * @param {string} agentId     — this agent's ID
 * @param {string} groupSecret — shared group secret
 * @param {string[]} members   — known members (optional)
 * @param {string} dir         — working directory
 */
function joinGroup(groupId, agentId, groupSecret, members = [], dir = process.cwd()) {
  const groupsDir = path.join(dir, GROUPS_DIR);
  fs.mkdirSync(groupsDir, { recursive: true });

  const groupConfig = {
    group_id:     groupId,
    agent_id:     agentId,
    group_secret: groupSecret,
    members,
    joined_at:    new Date().toISOString(),
    sil_version:  '1.6',
  };

  const filepath = path.join(groupsDir, `${groupId}.json`);
  fs.writeFileSync(filepath, JSON.stringify(groupConfig, null, 2));

  // Create group inbox
  const groupInbox = path.join(dir, INBOX_DIR, 'groups', groupId);
  fs.mkdirSync(groupInbox, { recursive: true });

  return groupConfig;
}

/**
 * Load a group config from local storage.
 */
function loadGroup(groupId, dir = process.cwd()) {
  const filepath = path.join(dir, GROUPS_DIR, `${groupId}.json`);
  if (!fs.existsSync(filepath)) return null;
  return JSON.parse(fs.readFileSync(filepath, 'utf8'));
}

/**
 * List all groups the agent is member of.
 */
function listGroups(dir = process.cwd()) {
  const groupsDir = path.join(dir, GROUPS_DIR);
  if (!fs.existsSync(groupsDir)) return [];
  return fs.readdirSync(groupsDir)
    .filter(f => f.endsWith('.json'))
    .map(f => JSON.parse(fs.readFileSync(path.join(groupsDir, f), 'utf8')));
}

// ============================================================
// SEND TO GROUP
// ============================================================

/**
 * Send a message to a group — encoded ONCE, readable by ALL members.
 * @param {string} message       — plaintext message
 * @param {string} intent        — SIL intent
 * @param {string} groupId       — group identifier
 * @param {string} senderAgentId — sender's agent ID
 * @param {string} groupSecret   — group shared secret
 * @param {string} dir           — working directory
 * @returns {object} { filepaths, enc_chunks }
 */
function sendGroup(message, intent, groupId, senderAgentId, groupSecret, dir = process.cwd()) {
  const enc_chunks = encode(message, groupSecret);
  const filepaths = [];

  enc_chunks.forEach((chunk) => {
    const msgId = crypto.createHash('sha256')
      .update(`${senderAgentId}${groupId}${message}${Date.now()}${chunk.chunkIndex}`)
      .digest('hex').slice(0, 16);

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const suffix = enc_chunks.length > 1 ? `_c${chunk.chunkIndex + 1}of${enc_chunks.length}` : '';
    const filename = `${timestamp}_${msgId}${suffix}_${intent}.sil`;

    const silContent = {
      header: {
        sil_version:  '1.6',
        protocol:     'SIL-Group/1.0',
        message_id:   msgId,
        group_id:     groupId,
        sender:       senderAgentId,
        recipient:    `group:${groupId}`,
        sent_at:      new Date().toISOString(),
        intent,
        'x-sil-nonce': chunk.nonce,
        scripts_used: chunk.langsUsed,
        gkl_checksum: chunk.gklGlobal,
        chunk_index:  chunk.chunkIndex,
        total_chunks: enc_chunks.length,
      },
      encoded: chunk.encoded,
      signature: crypto.createHash('sha256')
        .update(`${groupSecret}${chunk.encoded}`)
        .digest('hex'),
    };

    const groupInbox = path.join(dir, INBOX_DIR, 'groups', groupId);
    fs.mkdirSync(groupInbox, { recursive: true });
    const filepath = path.join(groupInbox, filename);
    fs.writeFileSync(filepath, JSON.stringify(silContent, null, 2), 'utf8');
    filepaths.push(filepath);
  });

  return { filepaths, enc_chunks };
}

// ============================================================
// RECEIVE FROM GROUP
// ============================================================

/**
 * Receive and decode all unread group messages.
 * @param {string} groupId     — group identifier
 * @param {string} agentId     — this agent's ID (to skip own messages)
 * @param {string} groupSecret — group shared secret
 * @param {string} dir         — working directory
 * @returns {object[]} decoded messages
 */
function receiveGroup(groupId, agentId, groupSecret, dir = process.cwd()) {
  const doneFile = path.join(dir, DONE_FILE);
  const processed = new Set(
    fs.existsSync(doneFile)
      ? fs.readFileSync(doneFile, 'utf8').split('\n').filter(Boolean)
      : []
  );

  const groupInbox = path.join(dir, INBOX_DIR, 'groups', groupId);
  if (!fs.existsSync(groupInbox)) return [];

  const files = fs.readdirSync(groupInbox)
    .filter(f => f.endsWith('.sil'))
    .map(f => path.join(groupInbox, f))
    .filter(f => !processed.has(f))
    .sort();

  const messages = [];
  for (const filepath of files) {
    try {
      const sil = JSON.parse(fs.readFileSync(filepath, 'utf8'));
      const { header, encoded, signature } = sil;

      // Skip own messages
      if (header.sender === agentId) {
        fs.appendFileSync(doneFile, filepath + '\n');
        continue;
      }

      // Verify signature
      const expectedSig = crypto.createHash('sha256')
        .update(`${groupSecret}${encoded}`)
        .digest('hex');
      const sigOk = signature === expectedSig;

      if (!sigOk) {
        messages.push({ filepath, error: 'INVALID_SIGNATURE', header });
        fs.appendFileSync(doneFile, filepath + '\n');
        continue;
      }

      // Decode
      const chunkIndex = header.chunk_index || 0;
      const nonce = header['x-sil-nonce'] || '';
      const dec = decodeChunk(encoded, groupSecret, chunkIndex, nonce);

      messages.push({
        filepath,
        header,
        groupId:   header.group_id,
        sender:    header.sender,
        intent:    header.intent,
        encoded,
        decoded:   dec.decoded,
        certain:   dec.certain,
        total:     dec.total,
        integrity: dec.integrity,
        sigOk,
      });

      fs.appendFileSync(doneFile, filepath + '\n');
    } catch (e) {
      messages.push({ filepath, error: e.message });
    }
  }

  return messages;
}

module.exports = {
  createGroup,
  joinGroup,
  loadGroup,
  listGroups,
  sendGroup,
  receiveGroup,
};
