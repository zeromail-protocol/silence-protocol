# @silence-protocol/sil

**Content-encrypted agent-to-agent communication.**

A2A solved interoperability. SIL solves confidentiality.

```bash
npm install -g @silence-protocol/sil
sil init
sil send "ANALYSE TENANT RIVOLI Q1 2026" --intent REQUEST
sil receive
```

## What is SIL?

The [A2A Protocol](https://a2a-protocol.org) (Google / Linux Foundation) defines the open standard for agent communication over HTTP. A2A sends message content as readable JSON — visible to cloud infrastructure, logging systems, and network monitors.

SIL is the confidentiality layer A2A doesn't provide. Messages are encoded into 6 ancient writing systems (Sumerian cuneiform, Mycenaean Linear B, Cypriot syllabary, Palmyrene script, Linear B Ideograms, Proto-Sinaitic) via HMAC-SHA256 key derivation. Without the shared secret, the content is opaque to any observer.

## How it looks

```
Message : "ANALYSE TENANT RIVOLI Q1 2026"

Encoded : 𐀀𐀣𐀉𐀊𐎃𐎍𐎋𐎅𐤇𐤍𐀏𐀆𐎎𐎈𐤉𐤍𐀅𐀍𐎍𐎁𐀋𐀘𐤘𐤄𞠘𞠡𐎆𐎞
Scripts : Linear B · Cuneiform · Palmyrene · Cypriot
Certain : 72/72 tokens
```

An interceptor sees 4 ancient civilizations. Without the key: noise.

## CLI

```bash
sil init                                    # Initialize canal
sil send "MESSAGE" --intent REQUEST         # Send
sil send "MESSAGE" --intent OFFER --push    # Send + git push
sil receive                                 # Receive
sil receive --pull                          # git pull + receive
sil status                                  # Canal status
sil encode "MESSAGE"                        # Encode only (test)
sil decode "𐀀𐀣..."                         # Decode only (test)
```

## Intents

`OFFER` · `REQUEST` · `INFO` · `ALERT` · `NEGOTIATION`

Responses: `ACCEPT` · `REFUSE` · `COUNTER` · `ESCALATE` · `DEFER`

## SDK Usage

```js
const { encode, decode, send, receive, init } = require('@silence-protocol/sil');
const { buildA2AMessage, decodeFromA2AMessage } = require('@silence-protocol/sil/a2a');
const { openRound, roundHeader } = require('@silence-protocol/sil/rounds');
const { humanToSIL, silToHuman } = require('@silence-protocol/sil/bridge');
const { createGroup, joinGroup, sendGroup, receiveGroup } = require('@silence-protocol/sil/group');
```

## A2A Bridge

SIL integrates with the [A2A Protocol](https://a2a-protocol.org) as an `application/x-sil` data part. Any A2A agent can carry SIL-encrypted content — agents without SIL see an opaque payload; agents with the shared secret decode it.

```js
const { buildA2AMessage, decodeFromA2AMessage, buildAgentCard, createA2AServer } = require('@silence-protocol/sil/a2a');

// Build A2A message with SIL encryption
const a2aMsg = buildA2AMessage('SCORE 745 REVENUS 4200', secret, sender, recipient, 'INFO');

// Decode on the other side
const result = decodeFromA2AMessage(a2aMsg, secret);
// result.decoded  → "SCORE 745 REVENUS 4200"
// result.sigOk    → true
// result.certain  → 22 (== result.total)

// Generate Agent Card (for /.well-known/agent.json)
const card = buildAgentCard('karine@scorent', 'Scoring agent', [
  { name: 'Tenant Scoring', description: 'Score locataire', tags: ['scoring'] }
]);

// Start A2A HTTP server
const server = createA2AServer(agentId, secret, card, async (decoded, raw) => {
  // decoded.decoded contains the decrypted SIL message
  return { text: 'Acknowledged' };
});
server.listen(3333);
```

A2A Part structure:

```json
{
  "parts": [{
    "data": {
      "x-sil-version": "1.5",
      "x-sil-encoded": "𐀀𐀣𐀉𐀊𐎃𐎍...",
      "x-sil-signature": "a1b2c3...",
      "x-sil-intent": "REQUEST",
      "x-sil-sender": "karine@scorent"
    },
    "mediaType": "application/x-sil"
  }]
}
```

## Rounds Protocol

Multi-turn conversation management between SIL agents.

```js
const { openRound, roundHeader, roundStatus, processRoundMessage } = require('@silence-protocol/sil/rounds');

// Initiator opens a round
const round = openRound('salomon@noctia', 'karine@scorent', 'SCORING RIVOLI', 'REQUEST');
// round.id    → "84a372f1-e356-43"
// round.state → "OPEN"

// Attach round metadata to SIL messages
const header = roundHeader(round, message, 'REQUEST');
// { 'x-round-id': '...', 'x-round-state': 'OPEN', 'x-round-turn': 0, ... }

// Process incoming round messages (state machine)
const updated = processRoundMessage(silContent, localRounds);
// States: OPEN → ACK → EXCHANGE → CLOSE

// Check round status
const status = roundStatus(round);
// { id, state, topic, turns, age_s, initiator, responder }
```

Round lifecycle: `OPEN` → `ACK` → `EXCHANGE` (N turns) → `CLOSE`

## Human Bridge

Bidirectional bridge between human natural language and SIL structured messages.

```js
const { humanToSIL, silToHuman } = require('@silence-protocol/sil/bridge');

// Human → SIL: strips noise, detects intent
const { message, intent } = humanToSIL("Donne moi le score du locataire Rivoli");
// message → "DONNE MOI LE SCORE DU LOCATAIRE RIVOLI"
// intent  → "REQUEST"

// SIL → Human: reintroduces natural language (via Claude API or fallback)
const natural = await silToHuman(
  'SCORE 745 REVENUS 4200 INCIDENTS 0',
  { channel: 'whatsapp', language: 'fr', topic: 'scoring Rivoli' },
  process.env.ANTHROPIC_API_KEY  // optional — falls back to basic formatting
);
// → "Le locataire Rivoli affiche un score de 745/1000, des revenus de 4 200€/mois..."
```

## Group Protocol (Multicast)

One message encrypted once, readable by all group members. One shared group secret instead of N bilateral channels.

### CLI

```bash
sil group create --id RIVOLI_PROJECT --members "salomon@noctia,karine@scorent,fiscal@fiscalready" --secret "group-secret"
sil group join --id RIVOLI_PROJECT --secret "group-secret"
sil group send "REUNION DEMAIN 14H" --group RIVOLI_PROJECT --intent INFO
sil group receive --group RIVOLI_PROJECT
sil group list
```

### SDK

```js
const { createGroup, joinGroup, sendGroup, receiveGroup, listGroups } = require('@silence-protocol/sil/group');

// Create a group
const group = createGroup('RIVOLI_PROJECT', [
  'salomon@noctia', 'karine@scorent', 'fiscal@fiscalready'
], 'group-secret', 'salomon@noctia');

// Each agent joins locally
joinGroup('RIVOLI_PROJECT', 'karine@scorent', 'group-secret', group.members);

// Send to group — encoded ONCE, readable by ALL members
sendGroup('REUNION DEMAIN 14H', 'INFO', 'RIVOLI_PROJECT', 'salomon@noctia', 'group-secret');

// Any member receives
const messages = receiveGroup('RIVOLI_PROJECT', 'karine@scorent', 'group-secret');
// messages[0].decoded  → "REUNION DEMAIN 14H"
// messages[0].certain  → 18/18
// messages[0].sigOk    → true
// messages[0].sender   → "salomon@noctia"

// Cross-secret isolation: wrong secret = invalid signature + garbage
```

## Example Conversation Output

```
[1] Human: "Donne moi le score du locataire Rivoli et les revenus"
[2] humanToSIL: "DONNE MOI LE SCORE DU LOCATAIRE RIVOLI ET LES REVENUS" (REQUEST)
[3] Round opened: 84a372f1 (OPEN)
[4] SIL encoded: 𞠂𞠍𐀊𐀣𐂋𐂢𐀅𐀴𐀃𐀬𒀉𒂓... (53 tokens)
[5] Karine decoded: 53/53 certain
[6] Karine (Claude): "SCORE 745 REVENUS 4200 INCIDENTS 0 ANCIENNETE 36 MOIS"
[7] SIL re-encoded: 52 tokens
[8] Salomon decoded: 52/52 certain
[9] silToHuman: "Le locataire Rivoli affiche un score de 745/1000,
    des revenus de 4 200€/mois et aucun incident
    sur les 12 derniers mois."
```

## Transport — Fork-SIL

SIL uses Git as transport. Each Git commit is the message signature. Zero additional infrastructure required.

```bash
# After sil send:
git add sil_inbox/ && git commit -m "SIL REQUEST" && git push

# On the other side:
git pull && sil receive
```

## Integrity — Proof by Nine

Every encoded token satisfies a universal mathematical property: `GKL_extended(SIGMA * 0.9) = 9`. Any observer can verify message integrity without the key.

```
(1) + (40) + (400) = 441 → GKL(441) = 9
Verified: 30/30
```

## Examples

```bash
node examples/test_a2a.js              # A2A Bridge end-to-end
node examples/test_conversation.js     # Full agent conversation
node examples/test_group.js            # Star topology (pairwise secrets)
node examples/test_group_broadcast.js  # Group protocol (shared secret)
```

## Repository

[github.com/zeromail-protocol/silence-protocol](https://github.com/zeromail-protocol/silence-protocol)

Priority date: 25 March 2026 · Hiram · Silence Protocol Initiative · Paris
