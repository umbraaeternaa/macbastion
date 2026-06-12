# 🜲 CHIMERA — a local-first security organism for macOS

CHIMERA is not a collection of tools. It is **one mind** orchestrating eight specialized
native organs — each unique alone, devastating together. It runs entirely on your machine:
**no cloud, no telemetry, no recovery paths.**

## What it does

The organism senses you and your environment, and reacts autonomously to protect you:

- **Senses** — operator fatigue (idle time, typing dynamics, behavioural drift), local
  threats (an on-device LLM flags anomalous events), and physical presence (a paired phone).
- **Reacts** — on a threat or condition, the core actuates cross-module reflexes: it locks
  your time-locked vault, starts decoy traffic, normalizes bandwidth, escalates a dead-man,
  or (only on your explicit opt-in) securely wipes.
- **Accounts** — every autonomous action is written to an append-only audit trail you can
  query: *"why did my vault lock?"*

## The eight organs

| Organ | Lang | Role |
|---|---|---|
| CHAFF  | C      | decoy HTTPS traffic — masks real patterns |
| ECHO   | C      | constant-rate bandwidth padding |
| ORACLE | Python | local LLM (Ollama) anomaly detection |
| MIRROR | C      | humanlike input jitter + privacy-preserving input sensing |
| PULSE  | C / Py | cognitive-load monitor — friction when you're tired |
| VAULT  | C      | time-locked storage, decrypted plaintext lives only in RAM |
| TETHER | C++    | Bluetooth dead-man — auto-lock if your phone leaves |
| PURGE  | C+asm  | secure erasure (ARM64 `dc zva`) — last resort |

A Python **core** is the brain: a JSON-RPC socket server the organs register with, the
reactive web that relays events into reflexes, a cognitive gate, and the audit trail.

## Quick start

Requirements: macOS on Apple Silicon · Homebrew · Python 3.11+ · [Ollama](https://ollama.com) (for ORACLE).

```bash
git clone https://github.com/umbraaeternaa/macbastion.git
cd macbastion/chimera

brew install openssl@3 libsodium          # native deps
./build.sh                                # venv + deps + all 8 organs

.venv/bin/python -m core up               # bring the organism alive
.venv/bin/python -m core status           # see it live (core + 8 organs + armed reflexes)
.venv/bin/python -m core watch            # stream its events
.venv/bin/python -m core audit            # the reflex audit trail
```

Run it permanently — starts at login, restarts if it crashes:

```bash
.venv/bin/python -m core plist > ~/Library/LaunchAgents/com.umbra.chimera.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.umbra.chimera.plist
# remove any time:
# launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.umbra.chimera.plist
```

Optional — **stable identity** so macOS permission grants (Accessibility for MIRROR,
Bluetooth for TETHER) survive rebuilds:

```bash
./sign.sh            # signs the native binaries with your Apple Development / Developer ID identity
./sign.sh -          # or ad-hoc (valid signature, but no stable identity)
```

An unsigned binary is identified by its content hash, which changes every rebuild, so its
grant resets; a signed binary keeps a stable designated requirement and the grant persists.

## Honest status

The brain and reactive intelligence are **complete and live-verified**: the organism
thinks, senses, reacts, and has **defended itself end-to-end on real hardware** — a flagged
ransomware event drove the vault to auto-lock and obfuscation to start, all recorded in the
audit trail. VAULT and ORACLE are functionally complete; MIRROR and PULSE sense for real.

The **last mile** is un-gating each organ's real OS effectors — the permissions a security
tool inherently needs: Accessibility (MIRROR/PULSE), Bluetooth + a paired phone (TETHER),
root for traffic shaping (CHAFF/ECHO), and code-signing for a stable identity. We build for
a year, not a week.

## Philosophy

One machine, one owner. Modules are organs. The brain matters more than the organs. No
imitations — an honest empty function beats a stub that pretends. Full law in `MANIFESTO.md`;
architecture in `docs/ARCHITECTURE.md`; current state in `STATE.md`.
