# 🛡️ macbastion

> Defensive security toolkit for macOS on Apple Silicon.
> Hardening, stealth mode, and ongoing audit — from one CLI.

![status](https://img.shields.io/badge/status-WIP-orange)
![macOS](https://img.shields.io/badge/macOS-26%2B-blue)
![arch](https://img.shields.io/badge/arch-Apple%20Silicon-purple)
![python](https://img.shields.io/badge/python-3.11%2B-yellow)
![license](https://img.shields.io/badge/license-MIT-green)

---

## What it does

**macbastion** is a layered defense system for macOS that gives you:

- 🔍 **Audit** — see exactly what's listening, who's broadcasting, what telemetry runs
- 🥷 **Stealth mode** — anonymize hostname, kill Apple discovery broadcasts, one-click toggle
- 🛡 **Hardening** — system configuration that survives reboots
- 📊 **Menu bar control** — SwiftBar plugin for live status + actions

Built as a **hybrid Python + native C/ARM64** project. Python handles UX and orchestration; native modules handle privileged or low-level work where it actually matters.

---

## Why

Modern macOS leaks identity by default:

- `rapportd` broadcasts your computer name on every network (AirDrop / Handoff)
- `symptomsd` ships network diagnostics to Apple 24/7
- Apple Analytics + Siri telemetry is on out of the box
- Microsoft Office, OneDrive, CCleaner, and similar leave dozens of background daemons that fone home
- Your Wi-Fi MAC is locked to each SSID forever in "Fixed" mode

macbastion gives you visibility into all of that, plus one-click toggles to opt out.

---

## Architecture
The hybrid design is intentional: Python gets you to a working CLI fast, native modules are added where they earn their cost (raw syscalls, hardware features, gauranteed memory ops).

---

## Defense layers

| Layer | Status | What it covers |
|-------|--------|----------------|
| **L0** Firmware / Boot | ✅ | FileVault, SIP, Gatekeeper, **Full Security** Secure Boot |
| **L1** System hardening | ✅ | Telemetry off, junk daemons removed, legacy kexts purged |
| **L1.5** Stealth mimicry | ✅ | Random hostname, mDNS off, Bonjour suppressed, BT toggle |
| **L2** Firewall | ⏳ | Little Snitch + pf integration |
| **L3** DNS | 🟢 | Cloudflared DoH (existing), Mullvad fallback (planned) |
| **L4** Anonymity routing | ⏳ | Mullvad VPN + Tor transparent proxy |
| **L5** Browser fingerprint | ⏳ | Mullvad Browser, hardened defaults |
| **L6** OPSEC / identity | ⏳ | Email aliases, password hygiene, Signal |
| **L7** Storage encryption | 🟢 | FileVault + VeraCrypt containers |
| **L8** Monitoring | ⏳ | macbastion-grown scanners + kqueue watchers |
| **L9** Panic mode | ⏳ | Secure wipe (ARM64 `dc zva`), dead-man switch |

---

## Quick start

```bash
git clone https://github.com/umbraaeternaa/macbastion.git
cd macbastion

# Python side
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Native side
make -C native/mac_spoof

# SwiftBar (optional)
brew install --cask swiftbar
./swiftbar/install.sh
```

---

## Usage

```bash
# Audit
macbastion scan ports               # listening sockets + exposure level

# Stealth mode (soft: hostname + broadcast off; AirDrop partial)
sudo macbastion stealth on          # enable
sudo macbastion stealth on --hard   # also kill Bluetooth, reboot recommended
sudo macbastion stealth off         # back to normal AirDrop mode
macbastion stealth status           # current state
macbastion stealth status --json    # machine-readable (for SwiftBar)
```

### Example: port audit on a fresh hardened machine
Listening Ports
---

## Design notes

### Why native modules at all
Python + `subprocess` is fine for orchestrating commands. But for things like:

- **Raw `ioctl(SIOCSIFLLADDR)`** — no shell-out, clean exit codes
- **`dc zva` cache zero** for guaranteed memory wipe — Python can't promise that
- **`kqueue`** file watchers — much lower overhead than polling
- **Hardware RNG access via syscall** — direct path to entropy

…native C earns its keep.

### Why SwiftBar instead of a full Cocoa app
For a prototype, SwiftBar gives you a menu bar item that executes shell scripts. Zero Xcode setup, zero notarization. Once the workflow is settled, converting to a proper Swift menubar app is straightforward — but ergonomic value comes first.

### Realism about macOS 26 + SIP
- `rapportd` cannot be live-killed (launchd on-demand XPC respawn under SIP). The `disable` flag is honored at the next boot only.
- Wi-Fi MAC spoofing via `SIOCSIFLLADDR` fails on Apple Silicon Wi-Fi (Apple-private partition). Apple's own per-SSID rotation is the actual lever; we make sure it's set to *Rotating* on every saved network.
- `mac_spoof` still works on USB-Ethernet adapters and is wired into the project for L8/L9 use.

These are not bugs — they're trade-offs we accept to keep SIP and Full Security enabled.

---

## Support development

CHIMERA is free, open source, and will stay that way. If the project is useful to
you and you want to support continued development, you can contribute via
**Monobank Jar** (Ukraine):

**https://send.monobank.ua/jar/AHaziFXjYX**

![Monobank QR Code](docs/donate.png)

See [docs/donate.md](docs/donate.md) for what donations fund — and, just as
importantly, what they explicitly do **not** change (the MANIFESTO and the
no-paywall philosophy).

---

## License

MIT
