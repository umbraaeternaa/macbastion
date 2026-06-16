#!/usr/bin/env python3
# <bitbar.title>CHIMERA organism monitor</bitbar.title>
# <bitbar.version>v0.1</bitbar.version>
# <bitbar.author>umbraaeternaa</bitbar.author>
# <bitbar.desc>Live status of the CHIMERA privacy organism — polls core.status (UX.md).</bitbar.desc>
# <swiftbar.refreshOnOpen>true</swiftbar.refreshOnOpen>
"""CHIMERA SwiftBar plugin (UX.md: swiftbar = passive state monitoring, polling every N s).
Connects to the core UNIX socket, calls core.status, renders the organism in the menu bar.
Read-only: it never commands the organism (dangerous/parameterised ops stay on the CLI, UX.md)."""
import json
import os
import socket

SOCK = os.path.expanduser("~/.config/chimera/run/core.sock")
REPO = "/Users/macbook/Projects/macbastion/chimera"
PY = f"{REPO}/.venv/bin/python"
N_ORGANS = 8


def query():
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(2)
    s.connect(SOCK)
    s.sendall(b'{"jsonrpc":"2.0","id":1,"method":"core.status"}\n')
    buf = b""
    while b"\n" not in buf:
        d = s.recv(65536)
        if not d:
            break
        buf += d
    s.close()
    return json.loads(buf.split(b"\n")[0])["result"]


def uptime(sec):
    sec = int(sec)
    h, m = sec // 3600, (sec % 3600) // 60
    return f"{h}h{m:02d}m" if h else f"{m}m"


def term(label, *cli):
    """A dropdown row that opens a CLI command in Terminal (cd repo first)."""
    cmd = f"cd {REPO} && {PY} -m core " + " ".join(cli)
    print(f"{label} | bash=/bin/zsh param1=-c param2={cmd!r} terminal=true")


try:
    r = query()
except Exception:
    print("🜲 ⛔ | color=red")
    print("---")
    print("CHIMERA core offline (socket unreachable) | color=red")
    term("Bring the organism up", "up")
    raise SystemExit(0)

core = r.get("core", {})
mods = r.get("modules", {})
reactive = r.get("reactive", {})
reg = sum(1 for m in mods.values() if m.get("status") == "registered")
total = len(mods) or N_ORGANS
color = "#34c759" if (reg == total == N_ORGANS) else ("#ff9500" if reg else "#ff3b30")

print(f"🜲 {reg}/{total} | color={color}")
print("---")
print(f"CHIMERA — core v{core.get('version', '?')}  (uptime {uptime(core.get('uptime_seconds', 0))}) | color=#888888")
mode = reactive.get("pulse_mode", "?")
print(f"Mind (PULSE): {mode} | color={'#34c759' if mode == 'normal' else '#ff9500'}")
print("---")
print("Organs | color=#888888")
for name in sorted(mods):
    m = mods[name]
    st = m.get("status", "?")
    nm = len(m.get("methods", []) or [])
    dot = "🟢" if st == "registered" else "🔴"
    print(f"{dot} {name}  [{st}]  ({nm}) | color={'#34c759' if st == 'registered' else '#ff3b30'}")
print("---")
refl = reactive.get("reflexes", []) or []
print(f"Reflexes armed: {len(refl)} | color=#888888")
for x in refl[:8]:
    print(f"-- {x}")
print("---")
term("Full status →", "status")
term("Reflex audit →", "audit")
print("CHIMERA on GitHub | href=https://github.com/umbraaeternaa/macbastion")
print("Refresh | refresh=true")
