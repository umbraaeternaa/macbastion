# 🜲 CHIMERA — a local-first security organism for macOS

> Not a collection of tools. **One mind** orchestrating eight specialized native organs —
> each unique alone, devastating together. It runs entirely on your machine:
> **no cloud, no telemetry, no recovery paths.**

![status](https://img.shields.io/badge/status-alpha-orange)
![macOS](https://img.shields.io/badge/macOS-Apple%20Silicon-purple)
![python](https://img.shields.io/badge/python-3.13-yellow)
![tests](https://img.shields.io/badge/tests-1109%20green-brightgreen)
![license](https://img.shields.io/badge/license-MIT-green)

CHIMERA senses you and your environment and reacts autonomously to protect you — then writes
every action to an audit trail you can question (*"why did my vault lock?"*). It lives in
[`chimera/`](chimera/); the wider **macbastion** hardening toolkit (below) is its umbrella.

---

## Quick start

Requirements: macOS on Apple Silicon · [Homebrew](https://brew.sh) · Python 3.13 · [Ollama](https://ollama.com).

```bash
git clone https://github.com/umbraaeternaa/macbastion.git
cd macbastion/chimera

./setup.sh                          # Homebrew deps + the ORACLE model + venv + all 8 organs
.venv/bin/python -m core up         # bring the organism alive
.venv/bin/python -m core status     # see it live
```

`setup.sh` configures itself on your Mac — installs the Homebrew C deps + the local LLM model,
builds every native organ, and never starts anything privileged behind your back. Full guide:
[`chimera/README.md`](chimera/README.md). Privileged + TCC-gated capabilities are self-signed,
by hand: [`chimera/deploy/INSTALL.md`](chimera/deploy/INSTALL.md).

---

## The eight organs

| Organ | Lang | Role |
|---|---|---|
| **CHAFF**  | C       | decoy HTTPS traffic — masks real patterns |
| **ECHO**   | C       | constant-rate bandwidth padding |
| **ORACLE** | Python  | local LLM (Ollama) anomaly detection |
| **MIRROR** | C       | humanlike input jitter + privacy-preserving input sensing |
| **PULSE**  | C / Py  | cognitive-load monitor — adds friction when you're tired |
| **VAULT**  | C       | time-locked storage; decrypted plaintext lives only in RAM |
| **TETHER** | C++     | Bluetooth dead-man — auto-locks if your phone leaves |
| **PURGE**  | C + asm | secure erasure (ARM64 `dc zva`) — the last resort |

A Python **core** is the brain: a JSON-RPC socket server the organs register with, a reactive
web that turns events into cross-module reflexes, a cognitive gate, and an append-only audit trail.

**How it behaves:** ORACLE flags an anomalous event → the core locks your VAULT, starts CHAFF
decoy traffic, normalizes bandwidth via ECHO, and heightens TETHER — then stands down when the
threat clears. Walk away with your phone → TETHER locks the screen through a root shim. Trigger a
panic → PURGE crypto-shreds the keys and zeroes RAM (operator-target file shred is opt-in).

---

## Honest status (MANIFESTO §4 — no imitations)

CHIMERA is **alpha**, built in the open. What is real today:

- ✅ Core + all 8 organs register and run live; autonomous reflexes fire **and stand down** on real hardware.
- ✅ ORACLE scores threats reliably with a local LLM (`qwen2.5:7b`): ransomware → ~1.0, routine → ~0.05.
- ✅ PURGE destruction is real end-to-end (Keychain + VAULT keys + state wipe + RAM zero + opt-in target shred).
- ✅ TETHER ranges a real BLE beacon; MIRROR injects real input; VAULT encrypts at rest, plaintext RAM-only.
- ⚠️ Deliberately gated: ECHO's real packet shaping (awaits a packet-root decision, §8); privileged + TCC
  capabilities need your own self-signed cert + macOS grants (Apple blocks scripting those — done by hand).
- ❌ **No notarization.** CHIMERA is one machine, one owner — you build and self-sign it locally. By design.

It refuses security theatre: it will **not** pretend to "wipe" unencrypted SSD data (wear-levelled flash
can't guarantee it) — it crypto-shreds keys instead, and tells you the honest limit.

---

## macbastion — the umbrella toolkit

The repository is **macbastion**, a layered macOS defense project; CHIMERA is its autonomous core.
The broader toolkit also gives you:

- 🔍 **Audit** — `macbastion scan ports`: what's listening, what's exposed.
- 🥷 **Stealth** — `sudo macbastion stealth on`: anonymize hostname, suppress Apple discovery broadcasts.
- 🛡 **Hardening** — telemetry off, junk daemons removed; SIP + FileVault + Full Security stay **ON**.
- 📊 **Menu bar** — a SwiftBar plugin for live status.

| Layer | Status | Covers |
|---|---|---|
| **L0** Firmware / Boot | ✅ | FileVault, SIP, Gatekeeper, Full Security |
| **L1** System hardening | ✅ | Telemetry off, junk daemons + legacy kexts purged |
| **L1.5** Stealth mimicry | ✅ | Random hostname, mDNS off, Bonjour suppressed |
| **L8** Monitoring | 🟢 | ORACLE anomaly detection + PULSE cognitive load *(CHIMERA)* |
| **L9** Panic mode | 🟢 | Secure erasure (`dc zva`) + Bluetooth dead-man *(CHIMERA: PURGE + TETHER)* |

---

## Support development

CHIMERA is free, open source, and will stay that way. If it's useful to you and you want to
support continued development — **Monobank Jar** (Ukraine):

**https://send.monobank.ua/jar/AHaziFXjYX**

<img src="docs/donate.png" alt="Monobank QR Code" width="320"/>

See [docs/donate.md](docs/donate.md) for what donations fund — and what they explicitly do **not**
change (the MANIFESTO and the no-paywall philosophy).

---

## License

MIT — see [LICENSE](LICENSE).
