"""
macbastion stealth — wrapper around stealth.sh bash backend.

Bash робить системні дії, Python надає structured I/O і CLI UX.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from rich.console import Console
from rich.table import Table

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STEALTH_SH = PROJECT_ROOT / "stealth" / "stealth.sh"

console = Console()


def _run(args: list[str], need_root: bool = False) -> tuple[int, str]:
    """Run stealth.sh with optional sudo. Returns (rc, combined output)."""
    cmd = [str(STEALTH_SH), *args]
    if need_root:
        cmd = ["sudo", *cmd]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode, (res.stdout + res.stderr).strip()
    except FileNotFoundError:
        return 127, f"stealth.sh not found at {STEALTH_SH}"


def _parse_status(raw: str) -> dict:
    """Parse stealth.sh status output into a dict."""
    state = {
        "mode": "unknown",
        "hostname": "?",
        "localhost": "?",
        "wifi_mac": "?",
        "rapportd": "?",
        "rapportd_disabled": "?",
        "airdrop": "?",
        "bluetooth": "?",
        "analytics": "?",
    }
    for line in raw.splitlines():
        s = line.strip()
        if "STEALTH MODE (SOFT)" in s:
            state["mode"] = "soft"
        elif "STEALTH MODE (HARD)" in s:
            state["mode"] = "hard"
        elif "AIRDROP MODE" in s:
            state["mode"] = "off"
        elif s.startswith("hostname:"):
            state["hostname"] = s.split(":", 1)[1].strip()
        elif s.startswith("localhost:"):
            state["localhost"] = s.split(":", 1)[1].strip()
        elif s.startswith("Wi-Fi MAC:"):
            state["wifi_mac"] = s.split(":", 1)[1].strip()
        elif s.startswith("rapportd:"):
            parts = s.split(":", 1)[1].strip()
            state["rapportd"] = parts.split()[0]
            if "yes" in parts:
                state["rapportd_disabled"] = "yes"
            elif "no" in parts:
                state["rapportd_disabled"] = "no"
        elif s.startswith("AirDrop:"):
            v = s.split(":", 1)[1].strip()
            state["airdrop"] = "on" if "✅" in v else ("partial" if "⚠" in v else "off")
        elif s.startswith("Bluetooth:"):
            state["bluetooth"] = "on" if "on" in s.split(":", 1)[1] else "off"
        elif s.startswith("Analytics:"):
            state["analytics"] = "off" if "OFF" in s else "on"
    return state


# ──────────────────────────────────────────────────────────
# public commands
# ──────────────────────────────────────────────────────────

def cmd_status(json_output: bool = False) -> int:
    rc, raw = _run(["status"])
    if rc != 0:
        if json_output:
            print(json.dumps({"error": raw}))
        else:
            console.print(f"[red]✗ {raw}[/red]")
        return rc

    state = _parse_status(raw)

    if json_output:
        print(json.dumps(state, indent=2))
        return 0

    mode_label = {
        "soft":    "🛡️  STEALTH MODE (SOFT)",
        "hard":    "🛡️🛡️ STEALTH MODE (HARD)",
        "off":     "📡  AIRDROP MODE",
        "unknown": "❓  UNKNOWN STATE",
    }[state["mode"]]
    color = {"soft": "yellow", "hard": "green", "off": "cyan", "unknown": "red"}[state["mode"]]
    console.print(f"\n[bold {color}]{mode_label}[/bold {color}]\n")

    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style="dim")
    t.add_column()
    t.add_row("hostname",   state["hostname"])
    t.add_row("localhost",  state["localhost"])
    t.add_row("Wi-Fi MAC",  state["wifi_mac"])
    t.add_row("rapportd",   f"{state['rapportd']}  (disabled flag: {state['rapportd_disabled']})")
    t.add_row("AirDrop",    state["airdrop"])
    t.add_row("Bluetooth",  state["bluetooth"])
    t.add_row("Analytics",  state["analytics"])
    console.print(t)
    console.print()
    return 0


def cmd_on(hard: bool = False) -> int:
    args = ["on"]
    if hard:
        args.append("--hard")
    rc, raw = _run(args, need_root=True)
    console.print(raw)
    return rc


def cmd_off() -> int:
    rc, raw = _run(["off"], need_root=True)
    console.print(raw)
    return rc
