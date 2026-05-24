#!/usr/bin/env python3
# <bitbar.title>macbastion stealth toggle</bitbar.title>
# <bitbar.version>v0.2</bitbar.version>
# <bitbar.author>umbraaeternaa</bitbar.author>
# <bitbar.desc>Stealth mode toggle for macbastion</bitbar.desc>
# <swiftbar.runInBash>false</swiftbar.runInBash>
# <swiftbar.refreshOnOpen>true</swiftbar.refreshOnOpen>
"""
macbastion SwiftBar plugin v0.2
────────────────────────────────
Calls external trigger scripts (not direct osascript) — avoids
SwiftBar's pipe-string quoting issues with embedded apostrophes.
"""

import json
import subprocess
from pathlib import Path

PROJECT  = Path.home() / "Projects" / "macbastion"
VENV_PY  = PROJECT / ".venv" / "bin" / "python"
TRIGGERS = Path.home() / ".config" / "macbastion" / "triggers"


def get_status() -> dict:
    if not VENV_PY.exists():
        return {"mode": "error", "error": f"venv python missing: {VENV_PY}"}
    try:
        r = subprocess.run(
            [str(VENV_PY), "-m", "macbastion.cli", "stealth", "status", "--json"],
            cwd=str(PROJECT), capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            return {"mode": "error", "error": (r.stdout + r.stderr).strip()}
        return json.loads(r.stdout)
    except Exception as e:
        return {"mode": "error", "error": str(e)}


def render():
    s = get_status()
    mode = s.get("mode", "unknown")

    # Top icon
    if mode == "soft":
        print("🛡 | color=orange size=14")
    elif mode == "hard":
        print("🛡 | color=green size=14")
    elif mode == "off":
        print("📡 | color=cyan size=14")
    elif mode == "error":
        print("⚠️ | color=red size=14")
    else:
        print("? | color=gray size=14")

    print("---")

    # Header
    headers = {
        "soft":  "🛡  STEALTH (SOFT)",
        "hard":  "🛡🛡 STEALTH (HARD)",
        "off":   "📡  AIRDROP MODE",
        "error": "⚠️  Error",
    }
    print(f"{headers.get(mode, 'Unknown')} | size=13")

    if mode == "error":
        print(f"{s.get('error', '?')[:80]} | color=red size=11 trim=false")
        print("---")
        print("🔄 Refresh | refresh=true")
        return

    # Status rows
    rows = [
        ("hostname",  s.get("hostname",  "?")),
        ("Wi-Fi MAC", s.get("wifi_mac",  "?")),
        ("rapportd",  f"{s.get('rapportd','?')} (disabled: {s.get('rapportd_disabled','?')})"),
        ("AirDrop",   s.get("airdrop",   "?")),
        ("Bluetooth", s.get("bluetooth", "?")),
        ("Analytics", s.get("analytics", "?")),
    ]
    for k, v in rows:
        print(f"{k}: {v} | font='Menlo' size=11 trim=false")

    print("---")
    print("Actions")

    on_sh     = TRIGGERS / "stealth-on.sh"
    on_hard   = TRIGGERS / "stealth-on-hard.sh"
    off_sh    = TRIGGERS / "stealth-off.sh"

    if mode == "off":
        print(f"🛡  Enable Stealth (Soft) | shell={on_sh} refresh=true terminal=false")
        print(f"🛡🛡 Enable Stealth (Hard) | shell={on_hard} refresh=true terminal=false")
    else:
        print(f"📡 Disable Stealth (Enable AirDrop) | shell={off_sh} refresh=true terminal=false")
        if mode == "soft":
            print(f"🛡🛡 Upgrade to HARD Stealth | shell={on_hard} refresh=true terminal=false")

    print("---")
    print("Quick")
    print(f"📂 Open Project Folder | shell=/usr/bin/open param1={PROJECT} terminal=false")
    print(f"🖥  Open Terminal in Project | shell=/usr/bin/open param1=-a param2=Terminal param3={PROJECT} terminal=false")
    print(f"🌐 GitHub Repo | href=https://github.com/umbraaeternaa/macbastion")
    print("---")
    print("🔄 Refresh now | refresh=true")


if __name__ == "__main__":
    render()
