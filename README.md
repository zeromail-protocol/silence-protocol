# Silence Protocol (SIL)

> *"Email was designed for humans who read. The coming world is populated by agents who act. Nobody rebuilt the protocol."*
>
> — SILENCE, the Founding Manifesto, March 2026

---

## What is this?

Silence Protocol (SIL) is a proposed communication protocol designed natively for AI agents. The core idea: agents don't need HTML, subject lines, marketing copy, or emotional punctuation. They need structured payloads, cryptographic signatures, and sub-500ms response semantics.

This repo contains:
- A conceptual specification (RFC v0.9)
- A manifesto (SILENCE)
- An agent implementation guide (including Fork-ZMP transport)
- A working Python prototype (v1.3)

---

## The problem

A typical commercial email is ~70% noise. The remaining 30% is the actual information. A human filters instinctively. An AI agent has to parse everything to find the signal.

As agents proliferate — booking flights, auditing accounts, negotiating contracts — they deserve a protocol built for them. Not adapted from one built for humans in 1971.

---

## What SIL proposes

- **SilZMF** — Structured message format. No HTML. No `?` or `!`. No urgency language. Just intent + data.
- **APP** — Agent Preference Profile: a living preference model that evolves from each ACCEPT/REFUSE decision.
- **SIL-Cipher** — A 7-layer encryption system. Each token is encoded into ancient script symbols via a key-derived language assignment.
- **Fork-SIL** — A Git-based transport using forks as exclusive bilateral channels. Zero infrastructure needed.
- **LKE** — Linguistic Key Exchange: each token is assigned a different ancient script by the shared secret. A single message mixes Phoenician, Cuneiform, Linear B, Ugaritic, Aramaic, and Proto-Sinaitic.

---

## The cipher — 6 ancient scripts

SIL-Cipher v1.3 implements the **Linguistic Key Exchange (LKE)**: each position in a message is assigned a different ancient writing system, derived from the shared secret via HMAC-SHA256.

```
HIRAM encoded in SIL-Cipher v1.3:

H → Phoenician   𐤔𐤔
I → Cuneiform    𒀀𒁿
R → Cuneiform    𒀄𒀣
A → Phoenician   𐤆𐤍
M → Cuneiform    𒀁𒁸

HIRAM = 𐤔𐤔𒀀𒁿𒀄𒀣𐤆𐤍𒀁𒁸
```

A longer message mixes all 6 scripts:

```
SILENCE PROTOCOL = 𐤕𐤌𒀀𒁿𒀂𒄹𐤉𐤀𒀁𒂜𐀁𐁠𒀁𒀌𐎆𐎙𐤕𐤏𒀅𒄃𐤌𐤋𐤖𐤀𐀌𐀍𒀂𒁹𐎙𐎜𐎑𐎏

Scripts used: Phoenician · Cuneiform · Linear B · Ugaritic
```

An interceptor sees a mix of 4 ancient civilizations. Without the key, there is no way to know which script corresponds to which token.

### The 6 scripts

| Code | Script | Origin | Unicode block |
|------|--------|---------|--------------|
| CU | Cuneiform | Sumerian, ~3400 BCE | U+12000 |
| LB | Linear B | Mycenaean Greek, ~1500 BCE | U+10000 |
| PH | Phoenician | Canaan, ~1050 BCE | U+10900 |
| AR | Imperial Aramaic | Near East, ~800 BCE | U+10840 |
| UG | Ugaritic | Syria, ~1400 BCE | U+10380 |
| PS | Proto-Sinaitic | Sinai, ~1900 BCE | U+1E800 |

### Integrity — the proof by nine

Every encoded symbol satisfies a universal mathematical property derived from Al-Khwarizmi's *Hisab al-Tis'a* (800 CE):

```
GKL_extended(SIGMA × 0.9) = 9   for every token, every message
```

This allows public integrity verification without the key. Anyone can verify a SIL message is intact. Nobody can read its content without the shared secret.

```
אמת = א(1) + מ(40) + ת(400) = 441 → GKL(441) = 9
```

---

## Quick start

```bash
git clone https://github.com/zeromail-protocol/silence-protocol
cd silence-protocol
pip install cryptography
python3 prototype/sil_cipher_v13.py
```

You will see:
- HELLO WORLD encoded across 4 ancient scripts
- Exact round-trip decode: 11/11 certain
- Proof-by-nine verified on every token: 30/30
- Wrong key → completely opaque output

---

## Addressing

SIL uses `name@domain` format:

```
moise@travelagentix
offers@airfrance
salomon@noctia
```

---

## Honest status

| Component | Status |
|-----------|--------|
| Protocol concept (ZMF, APP, intents) | Conceptual — peer review welcome |
| Fork-SIL transport | Workable — needs real-world testing |
| SIL-Cipher v1.3 | Encode + decode EXACT ✓ — not audited |
| LKE — 6 scripts | Working — 7/7 test messages pass |
| Cryptographic audit | **Required before any production use** |
| SDK | Not yet built |
| MCP server | Not yet built |

The prototype correctly demonstrates:
- Deterministic encoding with HMAC key
- Exact round-trip decode across all 6 ancient scripts
- Universal proof-by-nine (30/30 verified)
- Correct blocking with wrong key
- LKE: language per token derived from shared secret

---

## The 12 claims (priority date: March 2026)

1. **SIL** — Agent-native communication protocol
2. **LKE** — Linguistic Key Exchange (6 ancient scripts, token-level language assignment)
3. **GML** — Gematria Multi-System Layer (6 ancient numerical systems × 6 modes)
4. **SIGMA-222** — Semantic condensate (NP-hard, self-verifying)
5. **Script/phonetic dissociation** — writing and pronunciation languages independent
6. **GKL** — Gematria Ketana compression (אמת = 9)
7. **NLP** — Numeric Linguistic Protocol (numbers via canonical names)
8. **SIL-PR** — Cryptographic prompt watermarking
9. **GUI** — GKL Universal Integrity (proof-by-nine, universal)
10. **NPE** — Nine-Path Encoding (1 token → ancient symbols)
11. **Fork-SIL** — Git-based bilateral exclusive channel protocol
12. **SPP** — SIL Payment Protocol (Ed25519 double-signature triggered payment)

These are documented conceptual inventions, not granted patents. Cryptographic claims require independent verification.

---

## What we need

- **Cryptographers** to review and attack the SIL-Cipher specification
- **Protocol engineers** to stress-test the message format and Fork-SIL transport
- **Agent developers** to implement SIL in real agent systems
- **Honest criticism** — especially of the cryptographic claims

---

## Governance

BDFL model. **Hiram** (Silence Protocol Initiative, Paris) has final say on protocol decisions.

Changes proposed via **SIP** (Silence Improvement Proposals) — open a GitHub Issue tagged `SIP-XXX`, 30-day discussion, BDFL decides.

The protocol is open. The cipher implementation is the inventor's.

---

## License

Protocol specification: **MIT** — implement freely.
SIL-Cipher: © 2026 Hiram, Silence Protocol Initiative — all rights reserved pending audit.

---

*SILENCE — The Founding Manifesto — March 2026 — Paris*
*"The protocol belongs to everyone."*
