#!/usr/bin/env python3
"""CHIMERA reel — SVG cinematic frame generator (reel spec §2/§10/§14).

`frame(ts)` returns an SVG string for the whole timeline; render.py rasterises it
via cairosvg into PNG frames, then ffmpeg assembles (+grain +music). Style: cyberpunk
x steampunk x Interstellar — void bg, starfield, scanlines, an 8-node module ring,
the Umbra neuro-creature, a compass emblem, camera zoom/pan, glitch on cuts, a closing
monobank QR card. Text uses DejaVu Sans Mono (installed) with a Menlo/monospace fallback.

The per-reel content is the BRIEF dict (the agent overrides it per day).
"""

from __future__ import annotations

import json
import math
import os

W, H = 1080, 1920
FPS = 24
DUR = 45.0

# --- palette (spec §2, exact HEX) ---
VOID = "#050709"
CYAN = "#00F0FF"
MAGENTA = "#FF006E"
ACID = "#39FF14"
AMBER = "#FFB627"
DIM_AMBER = "#785616"
WHITE = "#D2E6E9"
MUTED = "#5F7880"
GHOST = "#1E343C"
VIOLET = "#9A6BFF"
TURQ = "#4FF0E0"
FONT = "DejaVu Sans Mono, Menlo, monospace"

# --- the per-reel brief (agent overrides) ---
BRIEF = {
    "day": 11,
    "subtitle": "THE MIND LEARNS TO REST",
    "tests": 734,
    "modules_done": 3,
    "lit": [0, 2, 3],        # done: CHAFF, ORACLE, MIRROR
    "focus": 4,              # PULSE — the day's work
    "labels": ["CHAFF", "ECHO", "ORACLE", "MIRROR", "PULSE", "VAULT", "TETHER", "PURGE"],
    "event": "PULSE :: BASELINE + ASSESS",
    "qr_png": "",  # base64 PNG injected by render.py (monobank)
}

# Per-session overrides (day, subtitle, event, lit, focus, tests) written by /reel.
_BRIEF_JSON = os.path.join(os.path.dirname(__file__), "brief.json")
if os.path.exists(_BRIEF_JSON):
    with open(_BRIEF_JSON, encoding="utf-8") as _f:
        BRIEF.update(json.load(_f))


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def smooth(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def fade(ts: float, t0: float, t1: float, hold: float, t2: float, t3: float) -> float:
    """0 -> 1 over [t0,t1], hold, 1 -> 0 over [t2,t3]."""
    if ts < t0 or ts > t3:
        return 0.0
    if ts < t1:
        return smooth((ts - t0) / (t1 - t0))
    if ts < t2:
        return 1.0
    return 1.0 - smooth((ts - t2) / (t3 - t2))


# --- deterministic star field ---
def _stars(ts: float) -> str:
    out = []
    for i in range(110):
        x = (i * 73 + 17) % W
        y = (i * 149 + 31) % H
        tw = 0.4 + 0.5 * (0.5 + 0.5 * math.sin(ts * 1.6 + i))
        r = 0.7 + (i % 3) * 0.5
        out.append(f'<circle cx="{x}" cy="{y}" r="{r:.1f}" fill="#cfe9ee" opacity="{tw:.2f}"/>')
    return "".join(out)


def _scanlines() -> str:
    return "".join(
        f'<rect x="0" y="{y}" width="{W}" height="1" fill="#000" opacity="0.06"/>'
        for y in range(0, H, 4)
    )


def _compass(cx: float, cy: float, r: float, ts: float, op: float) -> str:
    rot = ts * 14
    rays = []
    for i in range(8):
        a = math.radians(-90 + i * 45 + rot)
        x2, y2 = cx + r * math.cos(a), cy + r * math.sin(a)
        col = CYAN if i % 2 == 0 else AMBER
        rays.append(f'<line x1="{cx}" y1="{cy}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="{col}" stroke-width="3" opacity="{op*0.8:.2f}"/>')
    return (
        f'<g opacity="{op:.2f}">{"".join(rays)}'
        f'<circle cx="{cx}" cy="{cy}" r="{r*0.30:.0f}" fill="none" stroke="{CYAN}" stroke-width="4" filter="url(#glow)"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r*0.12:.0f}" fill="{CYAN}" filter="url(#glow)"/></g>'
    )


def _ring(cx: float, cy: float, r: float, ts: float, op: float) -> str:
    lit, focus, labels = BRIEF["lit"], BRIEF["focus"], BRIEF["labels"]
    parts = [f'<circle cx="{cx}" cy="{cy}" r="46" fill="{CYAN}" opacity="0.25" filter="url(#big)"/>',
             f'<circle cx="{cx}" cy="{cy}" r="26" fill="{CYAN}" filter="url(#glow)"/>']
    for i in range(8):
        a = math.radians(-90 + i * 45)
        nx, ny = cx + r * math.cos(a), cy + r * math.sin(a)
        is_lit = i in lit or i == focus
        col = CYAN if i in lit else (MAGENTA if i == focus else DIM_AMBER)
        pulse = 1.0 if i != focus else (0.6 + 0.4 * (0.5 + 0.5 * math.sin(ts * 4)))
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{nx:.0f}" y2="{ny:.0f}" stroke="{col}" stroke-width="2" opacity="{(0.5 if is_lit else 0.25):.2f}"/>')
        if is_lit:
            parts.append(f'<circle cx="{nx:.0f}" cy="{ny:.0f}" r="22" fill="{col}" opacity="{pulse:.2f}" filter="url(#glow)"/>')
        else:
            parts.append(f'<circle cx="{nx:.0f}" cy="{ny:.0f}" r="20" fill="none" stroke="{DIM_AMBER}" stroke-width="2" opacity="0.6"/>')
        lx = cx + (r + 58) * math.cos(a)
        ly = cy + (r + 58) * math.sin(a)
        parts.append(f'<text x="{lx:.0f}" y="{ly:.0f}" font-family="{FONT}" font-size="26" fill="{col}" text-anchor="middle" opacity="{(0.9 if is_lit else 0.45):.2f}">{labels[i]}</text>')
    return f'<g opacity="{op:.2f}">{"".join(parts)}</g>'


def _umbra(cx: float, cy: float, sc: float, ts: float, op: float) -> str:
    blink = 1.0 if (ts % 3.4) > 0.12 else 0.15
    eye_r = 52 * blink
    runes = []
    for i in range(12):
        a = math.radians(i * 30 + ts * 10)
        rx, ry = cx + 150 * sc * math.cos(a), cy - 30 * sc + 150 * sc * math.sin(a)
        col = VIOLET if i % 2 == 0 else CYAN
        runes.append(f'<circle cx="{rx:.0f}" cy="{ry:.0f}" r="4" fill="{col}" opacity="0.8" filter="url(#glow)"/>')
    return (
        f'<g opacity="{op:.2f}">'
        f'<ellipse cx="{cx}" cy="{cy+90*sc}" rx="{110*sc}" ry="{130*sc}" fill="url(#body)" stroke="#3a3f8a" stroke-width="2"/>'
        f'<ellipse cx="{cx}" cy="{cy-30*sc}" rx="{115*sc}" ry="{108*sc}" fill="url(#body)" stroke="#3a3f8a" stroke-width="2"/>'
        f'<path d="M{cx-70*sc},{cy-110*sc} L{cx-95*sc},{cy-175*sc} L{cx-40*sc},{cy-130*sc} Z" fill="url(#body)"/>'
        f'<path d="M{cx+70*sc},{cy-110*sc} L{cx+95*sc},{cy-175*sc} L{cx+40*sc},{cy-130*sc} Z" fill="url(#body)"/>'
        f'{"".join(runes)}'
        f'<circle cx="{cx}" cy="{cy-30*sc}" r="{eye_r*sc:.0f}" fill="url(#eye)" filter="url(#big)"/>'
        f'<circle cx="{cx-14*sc}" cy="{cy-44*sc}" r="{10*sc}" fill="#eafffd" opacity="0.9"/>'
        f'</g>'
    )


def _panel(text: str, col: str, op: float) -> str:
    return (
        f'<g opacity="{op:.2f}">'
        f'<rect x="60" y="1600" width="960" height="92" fill="{VOID}" opacity="0.72"/>'
        f'<rect x="60" y="1600" width="6" height="92" fill="{col}"/>'
        f'<text x="92" y="1658" font-family="{FONT}" font-size="34" fill="{WHITE}">{esc(text)}</text>'
        f'</g>'
    )


def _typed(text: str, x: int, y: int, ts: float, t0: float, col: str, size: int, op: float) -> str:
    n = max(0, int((ts - t0) * 22))
    shown = esc(text[:n])
    cur = "_" if int(ts * 2) % 2 == 0 else " "
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{col}" opacity="{op:.2f}">{shown}{cur}</text>'


# --- camera keyframes (t, scale, focus_x, focus_y) ---
KF = [
    (0, 1.0, 540, 900), (5, 1.0, 540, 760), (13, 1.28, 540, 720),
    (23, 1.34, 540, 900), (32, 0.9, 540, 820), (38, 0.9, 540, 820), (45, 0.9, 540, 820),
]


def _camera(ts: float) -> str:
    s, fx, fy = 1.0, 540, 900
    for i in range(len(KF) - 1):
        t0, s0, x0, y0 = KF[i]
        t1, s1, x1, y1 = KF[i + 1]
        if t0 <= ts <= t1:
            k = smooth((ts - t0) / (t1 - t0))
            s = s0 + (s1 - s0) * k
            fx = x0 + (x1 - x0) * k
            fy = y0 + (y1 - y0) * k
            break
    tx, ty = 540 - s * fx, 900 - s * fy
    return f"translate({tx:.1f} {ty:.1f}) scale({s:.3f})"


CUTS = [13, 23, 32, 38]


def _glitch(ts: float) -> str:
    for c in CUTS:
        if 0 <= ts - c < 0.22:
            dx = 8
            return (
                f'<g opacity="0.5"><rect x="0" y="{(int(ts*60)%H)}" width="{W}" height="40" fill="{MAGENTA}" opacity="0.12"/>'
                f'<rect x="{dx}" y="0" width="{W}" height="{H}" fill="{CYAN}" opacity="0.03"/></g>'
            )
    return ""


def _defs() -> str:
    return (
        '<defs>'
        f'<radialGradient id="void" cx="50%" cy="42%" r="75%"><stop offset="0%" stop-color="#0a1018"/><stop offset="100%" stop-color="{VOID}"/></radialGradient>'
        f'<radialGradient id="eye" cx="50%" cy="45%" r="60%"><stop offset="0%" stop-color="#eafffd"/><stop offset="45%" stop-color="{TURQ}"/><stop offset="100%" stop-color="#0e8f88"/></radialGradient>'
        '<linearGradient id="body" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1c1840"/><stop offset="55%" stop-color="#0c0a22"/><stop offset="100%" stop-color="#040310"/></linearGradient>'
        '<radialGradient id="vign" cx="50%" cy="50%" r="72%"><stop offset="60%" stop-color="#000" stop-opacity="0"/><stop offset="100%" stop-color="#000" stop-opacity="0.7"/></radialGradient>'
        '<filter id="glow"><feGaussianBlur stdDeviation="4"/></filter>'
        '<filter id="big"><feGaussianBlur stdDeviation="20"/></filter>'
        '<filter id="soft"><feGaussianBlur stdDeviation="2"/></filter>'
        '</defs>'
    )


def _qr_scene(ts: float, op: float) -> str:
    qr = BRIEF.get("qr_png", "")
    img = (f'<image x="325" y="720" width="430" height="430" href="data:image/png;base64,{qr}"/>'
           if qr else f'<rect x="325" y="720" width="430" height="430" fill="#fff"/>')
    return (
        f'<g opacity="{op:.2f}">'
        f'<rect x="305" y="700" width="470" height="470" fill="#fff" rx="14"/>{img}'
        f'<text x="540" y="1260" font-family="{FONT}" font-size="40" fill="{CYAN}" text-anchor="middle">SUPPORT THE BUILD</text>'
        f'<text x="540" y="1320" font-family="{FONT}" font-size="26" fill="{MUTED}" text-anchor="middle">monobank</text>'
        f'<text x="540" y="1700" font-family="{FONT}" font-size="26" fill="{MUTED}" text-anchor="middle">github.com/umbraaeternaa/macbastion</text>'
        f'</g>'
    )


def frame(ts: float) -> str:
    b = BRIEF
    world = (
        _compass(540, 760, 230, ts, fade(ts, 0.3, 1.5, 3.5, 5.5, 7.0))
        + _ring(540, 760, 300, ts, fade(ts, 4.5, 6.5, 24, 32, 38))
        + _umbra(540, 1150, 0.62, ts, fade(ts, 5.0, 7.0, 22, 30, 36))
    )
    screen = (
        f'<rect width="{W}" height="{H}" fill="url(#void)"/>'
        + _stars(ts)
        + f'<g filter="url(#soft)">{world if False else ""}</g>'
        + f'<g transform="{_camera(ts)}">{world}</g>'
    )
    # foreground HUD (screen-space, not camera-transformed)
    hud = _typed(f"> CHIMERA :: DAY {b['day']}", 90, 980, ts, 0.6, ACID, 46, fade(ts, 0.5, 1.2, 4.8, 5.8, 7.0))
    hud += _panel(b["event"], CYAN, fade(ts, 13.5, 14.5, 21, 22.5, 23.5))
    hud += _panel("THE GATE — SEALED, NOT YET OPENED", AMBER, fade(ts, 24, 25, 30, 31.5, 32.5))
    # title card 32-38
    tcard_op = fade(ts, 32.5, 33.5, 36.5, 37, 38)
    hud += (
        f'<g opacity="{tcard_op:.2f}" text-anchor="middle">'
        f'<text x="540" y="1380" font-family="{FONT}" font-size="64" fill="{WHITE}">DAY {b["day"]}</text>'
        f'<text x="540" y="1450" font-family="{FONT}" font-size="32" fill="{CYAN}">{esc(b["subtitle"])}</text>'
        f'<text x="540" y="1530" font-family="{FONT}" font-size="48" fill="{AMBER}">{b["modules_done"]} / 8</text>'
        f'<text x="540" y="1590" font-family="{FONT}" font-size="30" fill="{ACID}">{b["tests"]} TESTS GREEN</text>'
        f'</g>'
    )
    hud += _qr_scene(ts, fade(ts, 38.5, 39.5, 44, 44.5, 45))
    overlay = _scanlines() + f'<rect width="{W}" height="{H}" fill="url(#vign)"/>' + _glitch(ts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
        f'{_defs()}{screen}{hud}{overlay}</svg>'
    )
