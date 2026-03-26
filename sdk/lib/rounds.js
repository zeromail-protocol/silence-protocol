/**
 * SIL Rounds Protocol v1.0
 * 
 * Multi-turn conversation protocol between SIL agents.
 * 
 * Round lifecycle:
 * 1. OPEN    — initiator opens a round with a REQUEST or OFFER
 * 2. ACK     — responder acknowledges (ACCEPT or REFUSE)
 * 3. EXCHANGE— main exchange (N turns of INFO/REQUEST)
 * 4. CLOSE   — either agent closes the round (ACCEPT final)
 * 
 * Each round has a unique roundId.
 * All messages reference the roundId.
 * The round log is stored locally.
 */

const crypto = require('crypto');
const fs     = require('fs');
const path   = require('path');

const ROUNDS_DIR  = '.sil-rounds';
const ROUND_STATES = ['OPEN', 'ACK', 'EXCHANGE', 'CLOSE', 'REFUSED', 'EXPIRED'];

// ============================================================
// ROUND MANAGEMENT
// ============================================================

function getRoundsDir(dir = process.cwd()) {
  const p = path.join(dir, ROUNDS_DIR);
  fs.mkdirSync(p, { recursive: true });
  return p;
}

function saveRound(round, dir = process.cwd()) {
  const p = path.join(getRoundsDir(dir), `${round.id}.json`);
  fs.writeFileSync(p, JSON.stringify(round, null, 2));
}

function loadRound(roundId, dir = process.cwd()) {
  const p = path.join(getRoundsDir(dir), `${roundId}.json`);
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

function listRounds(dir = process.cwd()) {
  const d = getRoundsDir(dir);
  return fs.readdirSync(d)
    .filter(f => f.endsWith('.json'))
    .map(f => JSON.parse(fs.readFileSync(path.join(d, f), 'utf8')))
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
}

// ============================================================
// OPEN A ROUND
// ============================================================

/**
 * Open a new round.
 * Attaches roundId to the SIL message header.
 */
function openRound(initiator, responder, topic, intent = 'REQUEST', maxTurns = 10) {
  const round = {
    id:          crypto.randomUUID().slice(0, 16),
    state:       'OPEN',
    initiator,
    responder,
    topic,
    intent,
    max_turns:   maxTurns,
    turn:        0,
    created_at:  new Date().toISOString(),
    updated_at:  new Date().toISOString(),
    log:         [],
  };
  return round;
}

// ============================================================
// ROUND HEADER — added to SIL ZMF
// ============================================================

function roundHeader(round, messageText, messageIntent) {
  return {
    'x-round-id':     round.id,
    'x-round-state':  round.state,
    'x-round-turn':   round.turn,
    'x-round-intent': messageIntent,
    'x-round-topic':  round.topic,
  };
}

// ============================================================
// PROCESS INCOMING ROUND MESSAGE
// ============================================================

/**
 * Process an incoming SIL message that contains round metadata.
 * Returns updated round state.
 */
function processRoundMessage(silContent, localRounds = {}) {
  const header  = silContent.header || {};
  const roundId = header['x-round-id'];

  if (!roundId) return null;  // Not a round message

  let round = localRounds[roundId] || {
    id:         roundId,
    state:      header['x-round-state'] || 'OPEN',
    initiator:  header.sender,
    responder:  header.recipient,
    topic:      header['x-round-topic'] || '',
    turn:       header['x-round-turn'] || 0,
    created_at: new Date().toISOString(),
    log:        [],
  };

  // Add to log
  round.log.push({
    turn:      round.turn,
    from:      header.sender,
    intent:    header['x-round-intent'] || header.intent,
    timestamp: header.sent_at || new Date().toISOString(),
    message_id: header.message_id,
  });

  // State machine
  const incomingIntent = header['x-round-intent'] || header.intent;
  const currentState   = round.state;

  if (currentState === 'OPEN' && incomingIntent === 'ACCEPT') {
    round.state = 'EXCHANGE';
  } else if (currentState === 'OPEN' && incomingIntent === 'REFUSE') {
    round.state = 'REFUSED';
  } else if (currentState === 'EXCHANGE') {
    round.turn++;
    if (incomingIntent === 'ACCEPT' && round.turn > 1) {
      round.state = 'CLOSE';
    }
  }

  round.updated_at = new Date().toISOString();
  return round;
}

// ============================================================
// DECIDE RESPONSE INTENT
// ============================================================

/**
 * Given round state and incoming message, return appropriate response intent.
 */
function decideResponseIntent(round, incomingIntent, agentCapabilities = []) {
  switch (round.state) {
    case 'OPEN':
      // First message — acknowledge
      return agentCapabilities.length > 0 ? 'ACCEPT' : 'REFUSE';

    case 'EXCHANGE':
      // Mid-round — respond with INFO or ask more with REQUEST
      if (incomingIntent === 'INFO') return 'ACCEPT';
      if (incomingIntent === 'REQUEST') return 'INFO';
      if (incomingIntent === 'COUNTER') return 'COUNTER';
      return 'INFO';

    case 'CLOSE':
      return 'ACCEPT';

    default:
      return 'INFO';
  }
}

// ============================================================
// ROUND STATUS
// ============================================================

function roundStatus(round) {
  const age = Math.round((Date.now() - new Date(round.created_at)) / 1000);
  return {
    id:       round.id,
    state:    round.state,
    topic:    round.topic,
    turns:    round.turn,
    age_s:    age,
    initiator: round.initiator,
    responder: round.responder,
    last_update: round.updated_at,
  };
}

module.exports = {
  openRound,
  saveRound,
  loadRound,
  listRounds,
  roundHeader,
  processRoundMessage,
  decideResponseIntent,
  roundStatus,
  ROUND_STATES,
};
