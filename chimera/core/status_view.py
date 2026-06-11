"""Render the core.status payload into a readable operator view (UX.md — the CLI
surface). Pure + deterministic so it unit-tests without a socket; the `chimera status`
subcommand fetches core.status and prints render_status(result)."""

from __future__ import annotations

import time
from typing import Any


def render_event(topic: str, payload: dict[str, Any]) -> str:
    """Render one pushed event (topic + payload) as a concise operator line for
    `chimera watch`. Known critical topics get a friendly summary; anything else
    falls back to the raw topic (+ payload)."""
    p = payload or {}
    if topic == "tether.absent":
        return "TETHER: paired device absent (dead-man tripped)"
    if topic == "tether.escalation":
        return (
            f"TETHER: escalation {p.get('stage', '?')} -> {p.get('action_requested', '?')}"
        )
    if topic == "tether.recovered":
        return "TETHER: paired device recovered"
    if topic == "pulse.mode.changed":
        return f"PULSE: mode -> {p.get('new_mode', '?')}"
    if topic == "oracle.anomaly.detected":
        return f"ORACLE: anomaly detected (score {p.get('score', '?')})"
    if topic == "purge.imminent":
        return "PURGE: imminent — modules zeroing keys"
    if topic in ("vault.locked", "vault.unlocked", "vault.relocked"):
        return f"VAULT: {topic.split('.', 1)[1]}"
    return f"{topic} {p}" if p else topic


def render_audit(entries: list[dict[str, Any]]) -> str:
    """Render the reflex audit trail (AuditLog.recent()) as readable operator lines —
    the `chimera audit` surface. One line per actuation: local time, the firing topic ->
    the command(s) core issued, and the outcome (ok / error: ...). Empty -> a friendly
    notice, never a traceback."""
    lines = [f"CHIMERA — reflex audit ({len(entries)} entr{'y' if len(entries) == 1 else 'ies'})"]
    if not entries:
        lines.append("  (no reflexes actuated yet)")
        return "\n".join(lines)
    for e in entries:
        ts = e.get("ts")
        when = (
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
            if isinstance(ts, (int, float))
            else "?"
        )
        topic = e.get("topic", "?")
        cmds = ", ".join(e.get("commands", []) or []) or "-"
        outcome = e.get("outcome", "?")
        lines.append(f"  {when}  {topic} -> {cmds}  [{outcome}]")
    return "\n".join(lines)


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

    # Live VAULT state (queried from the daemon; offline when the module is down).
    vault = payload.get("vault")
    if vault is not None:
        if not vault.get("available", True):
            lines.append("VAULT: offline")
        elif vault.get("open"):
            lines.append(f"VAULT: open ({vault.get('open_vault_id', '?')})")
        else:
            lines.append("VAULT: locked")
    return "\n".join(lines)
