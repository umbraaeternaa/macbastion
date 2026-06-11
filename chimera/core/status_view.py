"""Render the core.status payload into a readable operator view (UX.md — the CLI
surface). Pure + deterministic so it unit-tests without a socket; the `chimera status`
subcommand fetches core.status and prints render_status(result)."""

from __future__ import annotations

from typing import Any


def render_status(payload: dict[str, Any]) -> str:
    """Render the core.status payload as a readable organism view: a core header
    (version + uptime) and one row per registered module (status, version, method
    count), sorted by name for stable output."""
    core = payload.get("core", {})
    version = core.get("version", "?")
    uptime = core.get("uptime_seconds", 0.0)
    modules = payload.get("modules", {})

    lines = [f"CHIMERA — core v{version}  (uptime {uptime:.0f}s)", f"{len(modules)} module(s):"]
    for name in sorted(modules):
        m = modules[name]
        status = str(m.get("status", "?"))
        mver = m.get("version", "?")
        n_methods = len(m.get("methods", []) or [])
        lines.append(f"  [{status:<8}] {name:<10} v{mver}  {n_methods} methods")

    # The "one mind": live cognitive mode + armed cross-module reflexes (when present).
    reactive = payload.get("reactive")
    if reactive:
        reflexes = reactive.get("reflexes", []) or []
        lines.append("")
        lines.append(f"PULSE: {reactive.get('pulse_mode', '?')}")
        lines.append(f"armed reflexes ({len(reflexes)}):")
        for r in reflexes:
            lines.append(f"  - {r}")
    return "\n".join(lines)
