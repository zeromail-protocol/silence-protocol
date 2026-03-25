# ZeroMail Protocol (ZMP)

> *"Email was designed for humans who read. The coming world is populated by agents who act. Nobody rebuilt the protocol."*
> 
> — SILENCE, the ZeroMail Manifesto, March 2026

---

## What is this?

ZeroMail is a proposed communication protocol designed natively for AI agents. The core idea: agents don't need HTML, subject lines, marketing copy, or emotional punctuation. They need structured payloads, cryptographic signatures, and sub-500ms response semantics.

This repo contains:
- A conceptual specification (RFC v0.9)
- A manifesto (SILENCE)
- An agent implementation guide (including Fork-ZMP transport)
- An early Python prototype

**This is not a finished protocol. This is a direction.**

---

## The problem

A typical commercial email is ~70% noise (HTML, styling, tracking pixels, persuasion copy). The remaining 30% is the actual information. A human filters instinctively. An AI agent has to parse everything to find the signal.

As agents proliferate — booking flights, auditing accounts, negotiating contracts — they deserve a protocol built for them. Not adapted from one built for humans in 1971.

---

## What ZMP proposes

- **ZMF** — ZeroMail Format: a structured JSON payload. No HTML. No `?` or `!`. No urgency language. Just intent + data.
- **APP** — Agent Preference Profile: a living preference model that evolves from each ACCEPT/REFUSE decision.
- **ZMP-Cipher** — A 7-layer encryption system combining AES-256, polyglot linguistic encoding, and ancient numerical systems (Hebrew Gematria, Greek Isopsephy, Arabic Abjad, Sanskrit Katapayadi, Japanese Iroha, Ethiopic Ge'ez).
- **Fork-ZMP** — A Git-based transport using forks as exclusive bilateral channels.
- **NPE / SIGMA-222** — A compression and integrity layer based on a universal mathematical property (the "casting out nines" / proof by nine, known since Al-Khwarizmi, 800 CE).

---

## Honest status

| Component | Status |
|-----------|--------|
| Protocol concept (ZMF, APP, intents) | Solid — peer review welcome |
| Fork-ZMP transport | Workable — needs real-world testing |
| ZMP-Cipher specification | Conceptually defined — **not audited** |
| Python prototype | Encodes correctly — decoding has collision issues |
| Cryptographic claims | **Require independent expert audit before any production use** |
| SDK | Not yet built |
| MCP server | Not yet built |

The prototype correctly demonstrates:
- Deterministic encoding with HMAC key
- Universal proof-by-nine (verified 30/30)
- Integrity verification without the key
- Correct blocking with wrong key

The prototype does **not** yet demonstrate:
- Exact round-trip decode (collision problem in ZTR_TABLE)
- Full ZMP-Cipher security as specified

---

## What we need

- **Cryptographers** to review and attack the ZMP-Cipher specification
- **Protocol engineers** to stress-test the ZMF format and Fork-ZMP transport
- **Agent developers** to try implementing ZMP in real agent systems
- **Honest criticism** — especially of the cryptographic claims

---

## The 12 claims (priority date: March 2026)

1. ZMP — Agent-native communication protocol
2. LKE — Linguistic Key Exchange (polyglot semantic deniability)
3. GML — Gematria Multi-System Layer (6 ancient systems × 6 modes)
4. SIGMA-222 — Semantic condensate (NP-hard, self-verifying)
5. Script/phonetic dissociation — independent writing and pronunciation languages
6. GKL — Gematria Ketana compression layer (אמת = 9)
7. NLP — Numeric Linguistic Protocol (numbers via canonical names)
8. ZMP-PR — Cryptographic prompt watermarking
9. GUI — GKL Universal Integrity (proof-by-nine, universal property)
10. NPE — Nine-Path Encoding (1 token → 1 cuneiform symbol)
11. Fork-ZMP — Git-based bilateral exclusive channel protocol
12. ZPP — ZMP Payment Protocol (Ed25519 double-signature triggered payment)

These are documented conceptual inventions, not granted patents. The cryptographic novelty claims (2–10) require independent verification.

---

## Quick start

```bash
git clone https://github.com/zeromail-protocol/zeromail
cd zeromail
pip install cryptography
python3 prototype/zmp_cipher_v09.py
```

You will see:
- HELLO WORLD encoded into cuneiform symbols
- Proof-by-nine verified on each symbol
- אמת = GKL(441) = 9 confirmed

---

## Addressing

ZMP uses `name@domain` format:

```
moise@travelagentix
offers@airfrance
salomon@noctia
```

---

## Governance

This project follows a BDFL model. **Hiram** (ZeroMail Initiative, Paris) has final say on protocol decisions.

Changes are proposed via **ZIP** (ZeroMail Improvement Proposals) — open a GitHub Issue tagged `ZIP-XXX`, discuss for 30 days, then BDFL decides.

The protocol is open. The cipher implementation is the inventor's.

---

## License

Protocol specification: **MIT** — implement freely.  
ZMP-Cipher specification: © 2026 Hiram, ZeroMail Initiative — all rights reserved pending audit.

---

## Contact

Issues and pull requests welcome.  
For cryptographic audit proposals: open an Issue.  
For everything else: open an Issue.

---

*SILENCE — The ZeroMail Manifesto — March 2026 — Paris*  
*"The protocol belongs to everyone."*
