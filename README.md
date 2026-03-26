# Silence Protocol (SIL)

> *"Email was designed for humans who read. The coming world is populated by agents who act. Nobody rebuilt the protocol."*
>
> --- SILENCE, the Founding Manifesto, March 2026

---

## Install

```bash
npm install -g @silence-protocol/sil
```

**npm**: [npmjs.com/package/@silence-protocol/sil](https://www.npmjs.com/package/@silence-protocol/sil)

```bash
sil init --agent karine@scorent --recipient salomon@noctia --secret MY_SECRET
sil send "ANALYSE TENANT RIVOLI Q1 2026" --intent REQUEST
sil receive
```

---

## What is SIL?

The [A2A Protocol](https://a2a-protocol.org) (Google / Linux Foundation) defines the open standard for agent communication over HTTP. A2A sends message content as readable JSON --- visible to cloud infrastructure, logging systems, and network monitors.

SIL is the confidentiality layer A2A doesn't provide. Messages are encoded into 6 ancient writing systems via HMAC-SHA256 key derivation. Without the shared secret, the content is opaque to any observer.

This repo contains:
- The protocol specification (RFC v1.3)
- The founding manifesto (SILENCE)
- An agent implementation guide
- Python prototype (`prototype/`)
- Node.js SDK (`sdk/`) --- published as `@silence-protocol/sil`

---

## The cipher --- 6 ancient scripts

SIL-Cipher v1.5 implements the **Linguistic Key Exchange (LKE)**: each position in a message is assigned a different ancient writing system, derived from the shared secret via HMAC-SHA256.

```
Message : "SOLDE RIVOLI"
Encoded : 𞠈𞠜𐀊𐀣𐂉𐃢𐀁𐁮𐀃𐀬𒀉𒂓𐀉𐀐𞠕𞠬𐠟𐠟𞠊𞠖𐢏𐢇𐢍𐢧
Scripts : Proto-Sinaitic · Linear B · Cuneiform · Cypriot · Palmyrene
Certain : 12/12 tokens
```

An interceptor sees 5 ancient civilizations. Without the key: noise.

### The 6 scripts

| Code | Script | Origin | Unicode block |
|------|--------|---------|--------------|
| CU | Cuneiform | Sumerian, ~3400 BCE | U+12000 (400 symbols) |
| LB | Linear B | Mycenaean Greek, ~1500 BCE | U+10000 (127 symbols) |
| LB2 | Linear B Ideograms | Mycenaean, ~1500 BCE | U+10080 (120 symbols) |
| CP | Cypriot | Cyprus, ~800 BCE | U+10800 (50 symbols) |
| PM | Palmyrene | Palmyra, ~100 BCE | U+10880 (50 symbols) |
| PS | Proto-Sinaitic | Sinai, ~1900 BCE | U+1E800 (45 symbols) |

### Integrity --- the proof by nine

Every encoded symbol satisfies a universal mathematical property derived from Al-Khwarizmi's *Hisab al-Tis'a* (800 CE):

```
GKL_extended(SIGMA x 0.9) = 9   for every token, every message
```

This allows public integrity verification without the key. Anyone can verify a SIL message is intact. Nobody can read its content without the shared secret.

```
aleph-mem-tav = aleph(1) + mem(40) + tav(400) = 441 -> GKL(441) = 9
```

---

## CLI

```bash
sil init                                    # Initialize canal (interactive)
sil init --agent A --recipient B --secret S # Initialize canal (flags)
sil send "MESSAGE" --intent REQUEST         # Send
sil send "MESSAGE" --intent OFFER --push    # Send + git push
sil receive                                 # Receive and decode
sil receive --pull                          # git pull + receive
sil status                                  # Canal status
sil encode "MESSAGE"                        # Encode only (test)
sil decode "encoded..."                     # Decode only (test)
```

### Intents

`OFFER` . `REQUEST` . `INFO` . `ALERT` . `NEGOTIATION`

Responses: `ACCEPT` . `REFUSE` . `COUNTER` . `ESCALATE` . `DEFER`

---

## SDK Usage

```js
const { encode, decode, send, receive, init } = require('@silence-protocol/sil');
const { buildA2AMessage, decodeFromA2AMessage } = require('@silence-protocol/sil/a2a');
const { openRound, roundHeader } = require('@silence-protocol/sil/rounds');
const { humanToSIL, silToHuman } = require('@silence-protocol/sil/bridge');
```

---

## A2A Bridge (`lib/a2a_bridge.js`)

SIL integrates with the [A2A Protocol](https://a2a-protocol.org) as an `application/x-sil` data part. Any A2A agent can carry SIL-encrypted content --- agents without SIL see an opaque payload; agents with the shared secret decode it.

```js
const {
  buildA2AMessage,
  decodeFromA2AMessage,
  buildAgentCard,
  createA2AServer,
  hasSILParts,
} = require('@silence-protocol/sil/a2a');

// Build A2A JSON-RPC message with SIL encryption
const a2aMsg = buildA2AMessage(
  'SCORE 745 REVENUS 4200',
  sharedSecret,
  'karine@scorent',
  'salomon@noctia',
  'INFO'
);

// Decode on the recipient side
const result = decodeFromA2AMessage(a2aMsg, sharedSecret);
// result.decoded  -> "SCORE 745 REVENUS 4200"
// result.sigOk    -> true
// result.certain  -> 22 (== result.total)
// result.intent   -> "INFO"
// result.sender   -> "karine@scorent"

// Generate Agent Card (served at /.well-known/agent.json)
const card = buildAgentCard('karine@scorent', 'Scoring immobilier agent', [
  { name: 'Tenant Scoring', description: 'Score locataire', tags: ['scoring'] },
  { name: 'Revenue Analysis', description: 'Analyse revenus', tags: ['finance'] },
], 'https://scorent.io/a2a');

// Start minimal A2A HTTP server
const server = createA2AServer(agentId, secret, card, async (decoded, rawA2A) => {
  // decoded.decoded = decrypted SIL message
  // decoded.intent  = SIL intent
  // decoded.sender  = sender agent ID
  return { text: 'Acknowledged' };
});
server.listen(3333);
```

### A2A Part structure

```json
{
  "parts": [{
    "data": {
      "x-sil-version": "1.5",
      "x-sil-encoded": "encoded-ancient-symbols...",
      "x-sil-signature": "hmac-sha256-hex",
      "x-sil-intent": "REQUEST",
      "x-sil-sender": "karine@scorent"
    },
    "mediaType": "application/x-sil"
  }]
}
```

---

## Rounds Protocol (`lib/rounds.js`)

Multi-turn conversation management between SIL agents.

```js
const {
  openRound,
  roundHeader,
  processRoundMessage,
  roundStatus,
  decideResponseIntent,
} = require('@silence-protocol/sil/rounds');

// Initiator opens a round
const round = openRound(
  'salomon@noctia',    // initiator
  'karine@scorent',    // responder
  'SCORING RIVOLI',    // topic
  'REQUEST',           // intent
  10                   // max turns
);
// round.id    -> "84a372f1-e356-43"
// round.state -> "OPEN"

// Attach round metadata to SIL message headers
const header = roundHeader(round, message, 'REQUEST');
// {
//   'x-round-id':    '84a372f1-e356-43',
//   'x-round-state': 'OPEN',
//   'x-round-turn':  0,
//   'x-round-intent':'REQUEST',
//   'x-round-topic': 'SCORING RIVOLI'
// }

// Process incoming messages (state machine)
const updated = processRoundMessage(silContent, localRounds);
// State transitions: OPEN -> ACK -> EXCHANGE (N turns) -> CLOSE

// Decide response intent automatically
const responseIntent = decideResponseIntent(round, 'REQUEST', ['scoring']);
// -> 'INFO' (agent has capabilities, responds with information)

// Check round status
const status = roundStatus(round);
// { id, state, topic, turns, age_s, initiator, responder, last_update }
```

### Round lifecycle

```
OPEN -----> ACK -----> EXCHANGE (N turns) -----> CLOSE
  |
  +-------> REFUSED (responder declines)
  +-------> EXPIRED (timeout)
```

---

## Human Bridge (`lib/bridge.js`)

Bidirectional bridge between human natural language and SIL structured messages.

```js
const { humanToSIL, silToHuman, processHumanInput, processForHuman } = require('@silence-protocol/sil/bridge');

// Human -> SIL: strips noise, detects intent
const { message, intent } = humanToSIL(
  "Donne moi le score du locataire Rivoli et les revenus"
);
// message -> "DONNE MOI LE SCORE DU LOCATAIRE RIVOLI ET LES REVENUS"
// intent  -> "REQUEST" (detected from "donne")

// SIL -> Human: reintroduces natural language via Claude API
const natural = await silToHuman(
  'SCORE 745 REVENUS 4200 INCIDENTS 0',
  { channel: 'whatsapp', language: 'fr', topic: 'scoring Rivoli' },
  process.env.ANTHROPIC_API_KEY   // optional: falls back to basic formatting
);
// -> "Le locataire Rivoli affiche un score de 745/1000,
//     des revenus de 4 200 EUR/mois et aucun incident."

// Full pipeline helpers
const payload = processHumanInput(humanText, senderAgent, recipientAgent);
const output  = await processForHuman(silDecoded, context, apiKey);
```

### Intent detection keywords

| Intent | Keywords |
|--------|----------|
| REQUEST | solde, score, analyse, donne, montre, cherche... |
| OFFER | propose, offre, je veux, disponible, tarif... |
| ALERT | urgent, alerte, probleme, incident, attention... |
| NEGOTIATION | negocie, contre-proposition, discount... |
| INFO | (default) |

---

## Agent Groups (Star Topology)

Multiple agents with pairwise secrets. The orchestrator broadcasts to all and aggregates responses.

```js
const { encode, decode } = require('@silence-protocol/sil');

// Each pair has its own shared secret
const secrets = {
  'salomon-karine': 'secret-scoring-channel',
  'salomon-fiscal': 'secret-fiscal-channel',
};

// Broadcast same request, different secrets
const encKarine = encode('ANALYSE RIVOLI', secrets['salomon-karine']);
const encFiscal = encode('ANALYSE RIVOLI', secrets['salomon-fiscal']);

// Each agent decodes with its own secret
const decK = decode(encKarine[0].encoded, secrets['salomon-karine']);
const decF = decode(encFiscal[0].encoded, secrets['salomon-fiscal']);
// Both: "ANALYSE RIVOLI" --- 100% certain

// Cross-secret isolation: Karine cannot read Fiscal's messages
const cross = decode(encKarine[0].encoded, secrets['salomon-fiscal']);
// cross.decoded -> garbage (cryptographically isolated)
```

---

## Real Conversation Example

```
[1] Human: "Donne moi le score du locataire Rivoli et les revenus"

[2] Bridge humanToSIL():
    Clean:  "DONNE MOI LE SCORE DU LOCATAIRE RIVOLI ET LES REVENUS"
    Intent: REQUEST

[3] Round opened: 84a372f1 (OPEN, topic: SCORING RIVOLI)

[4] Salomon encodes SIL:
    Encoded: 53 tokens across 6 ancient scripts
    GKL checksum: 3

[5] Karine decodes:
    "DONNE MOI LE SCORE DU LOCATAIRE RIVOLI ET LES REVENUS"
    Certain: 53/53 (100%)

[6] Karine calls Claude API (persona: scoring agent):
    Response: "SCORE 745 REVENUS 4200 INCIDENTS 0 ANCIENNETE 36 MOIS GARANTIE VISALE"

[7] Karine encodes SIL INFO response:
    69 tokens, 6 scripts

[8] Salomon decodes:
    "SCORE 745 REVENUS 4200 INCIDENTS 0 ANCIENNETE 36 MOIS GARANTIE VISALE"
    Certain: 69/69 (100%)

[9] Bridge silToHuman() via Claude API:
    "Le locataire Rivoli affiche un score de 745/1000,
     des revenus de 4 200 EUR/mois et aucun incident
     sur les 36 derniers mois. Garantie Visale active."

[10] Round status: EXCHANGE (turn 1)
```

---

## Transport --- Fork-SIL

SIL uses Git as transport. Each Git commit is the message signature. Zero additional infrastructure required.

```bash
# After sil send:
git add sil_inbox/ && git commit -m "SIL REQUEST" && git push

# On the other side:
git pull && sil receive
```

---

## Repository structure

```
silence-protocol/
  README.md
  LICENSE
  EN_SILENCE_Manifesto_SIL_Hiram_March2026.html
  EN_SIL_12_Claims_Priority_March2026.html
  EN_SIL_Agent_Guide_v11.html
  EN_SIL_RFC_v13_March2026.html
  prototype/
    sil_cipher_v15.js          # SIL-Cipher v1.5 (Node.js)
    sil_cipher_v15.py          # SIL-Cipher v1.5 (Python)
    a2a_bridge.js              # A2A Bridge
    rounds.js                  # Rounds Protocol
    bridge.js                  # Human Bridge
    sil_agent_loop_v2.py       # Agent loop (Python)
    sil_agent_karine_v2.json   # Karine agent config
    sil_agent_salomon_v2.json  # Salomon agent config
    zmp_v15.py                 # ZMF v1.5 (Python)
  sdk/                         # npm package source
    lib/
      cipher.js                # SIL-Cipher v1.5
      index.js                 # SDK entry point
      a2a_bridge.js            # A2A Bridge
      rounds.js                # Rounds Protocol
      bridge.js                # Human Bridge
    bin/sil.js                 # CLI
    examples/
      test_a2a.js              # A2A end-to-end test
      test_conversation.js     # Real agent conversation
      test_group.js            # Star topology group test
    package.json
```

---

## Quick start (Python prototype)

```bash
git clone https://github.com/zeromail-protocol/silence-protocol
cd silence-protocol
pip install cryptography
python3 prototype/sil_cipher_v15.py
```

## Quick start (Node.js SDK)

```bash
npm install -g @silence-protocol/sil
sil init --agent alice@domain --recipient bob@other --secret MY_SECRET
sil send "HELLO WORLD" --intent INFO
sil receive
```

```bash
# Run examples
cd sdk
npm install
node examples/test_a2a.js
node examples/test_conversation.js
node examples/test_group.js
```

---

## The 12 claims (priority date: March 2026)

1. **SIL** --- Agent-native communication protocol
2. **LKE** --- Linguistic Key Exchange (6 ancient scripts, token-level language assignment)
3. **GML** --- Gematria Multi-System Layer (6 ancient numerical systems x 6 modes)
4. **SIGMA-222** --- Semantic condensate (NP-hard, self-verifying)
5. **Script/phonetic dissociation** --- writing and pronunciation languages independent
6. **GKL** --- Gematria Ketana compression (aleph-mem-tav = 9)
7. **NLP** --- Numeric Linguistic Protocol (numbers via canonical names)
8. **SIL-PR** --- Cryptographic prompt watermarking
9. **GUI** --- GKL Universal Integrity (proof-by-nine, universal)
10. **NPE** --- Nine-Path Encoding (1 token to ancient symbols)
11. **Fork-SIL** --- Git-based bilateral exclusive channel protocol
12. **SPP** --- SIL Payment Protocol (Ed25519 double-signature triggered payment)

These are documented conceptual inventions, not granted patents. Cryptographic claims require independent verification.

---

## Honest status

| Component | Status |
|-----------|--------|
| Protocol concept (ZMF, APP, intents) | Conceptual --- peer review welcome |
| Fork-SIL transport | Workable --- needs real-world testing |
| SIL-Cipher v1.5 | Encode + decode EXACT --- not audited |
| LKE --- 6 scripts (>= 45 symbols each) | Working --- zero collisions across 37 token types |
| A2A Bridge | Working --- full JSON-RPC 2.0 + Agent Card |
| Rounds Protocol | Working --- multi-turn state machine |
| Human Bridge | Working --- Claude API + fallback |
| npm SDK (`@silence-protocol/sil`) | Published v1.5.1 |
| Cryptographic audit | **Required before any production use** |

---

## What we need

- **Cryptographers** to review and attack the SIL-Cipher specification
- **Protocol engineers** to stress-test the message format and Fork-SIL transport
- **Agent developers** to implement SIL in real agent systems
- **Honest criticism** --- especially of the cryptographic claims

---

## Governance

BDFL model. **Hiram** (Silence Protocol Initiative, Paris) has final say on protocol decisions.

Changes proposed via **SIP** (Silence Improvement Proposals) --- open a GitHub Issue tagged `SIP-XXX`, 30-day discussion, BDFL decides.

The protocol is open. The cipher implementation is the inventor's.

---

## License

Protocol specification: **MIT** --- implement freely.
SIL-Cipher: (c) 2026 Hiram, Silence Protocol Initiative --- all rights reserved pending audit.

---

*SILENCE --- The Founding Manifesto --- March 2026 --- Paris*
*"The protocol belongs to everyone."*
