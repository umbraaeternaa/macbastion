#!/usr/bin/env python3
"""CHIMERA reel — SVG cinematic frame generator with a daily variation engine.

`frame(ts)` returns an SVG string for the whole timeline; render.py rasterises it via
cairosvg, then ffmpeg assembles (+grain +music). Style: cyberpunk x steampunk x
Interstellar — void, animated background, an 8-node module ring, the Umbra creature,
camera moves, glitch, a closing monobank QR card.

DAILY VARIATION (seed = brief["variant_seed"] or the day number): the accent palette,
background style, camera path and Umbra eye colour are chosen per day, so every reel is
recognisably CHIMERA yet fresh. MOTION: drifting background, beat-pulse on nodes/core/
eye, colour shimmer, a breathing Umbra. Text = DejaVu Sans Mono (Menlo fallback).
"""

from __future__ import annotations

import json
import math
import os
import random

W, H = 1080, 1920
FPS = 24
DUR = 45.0

# palette (spec §2)
VOID = "#050709"
CYAN = "#00F0FF"
MAGENTA = "#FF006E"
ACID = "#39FF14"
AMBER = "#FFB627"
DIM_AMBER = "#785616"
WHITE = "#D2E6E9"
MUTED = "#5F7880"
VIOLET = "#9A6BFF"
TURQ = "#4FF0E0"
FONT = "DejaVu Sans Mono, Menlo, monospace"

BRIEF = {
    "day": 11,
    "subtitle": "THE MIND LEARNS TO REST",
    "tests": 734,
    "modules_done": 3,
    "lit": [0, 2, 3],
    "focus": 4,
    "labels": ["CHAFF", "ECHO", "ORACLE", "MIRROR", "PULSE", "VAULT", "TETHER", "PURGE"],
    "event": "PULSE :: BASELINE + ASSESS",
    "qr_png": "",
    "variant_seed": None,  # defaults to day
}

_BRIEF_JSON = os.path.join(os.path.dirname(__file__), "brief.json")
if os.path.exists(_BRIEF_JSON):
    with open(_BRIEF_JSON, encoding="utf-8") as _f:
        BRIEF.update(json.load(_f))

# --- daily variation engine ---
_SCHEMES = [
    (CYAN, MAGENTA), (VIOLET, TURQ), (ACID, AMBER),
    (MAGENTA, CYAN), (AMBER, CYAN), (TURQ, VIOLET), (CYAN, ACID),
]
_BGS = ["stars", "flow", "grid"]
_CAMS = ["push", "pull", "drift"]
_EYES = [TURQ, VIOLET, CYAN]


def _variant() -> dict:
    seed = BRIEF.get("variant_seed") or BRIEF.get("day", 0)
    r = random.Random(seed)
    a1, a2 = _SCHEMES[seed % len(_SCHEMES)]  # guaranteed daily colour rotation
    return {"a1": a1, "a2": a2, "bg": r.choice(_BGS), "cam": r.choice(_CAMS),
            "eye": r.choice(_EYES), "seed": seed}


V = _variant()
BPM = 132.0  # visual pulse tempo


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def smooth(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def fade(ts, t0, t1, hold, t2, t3):
    if ts < t0 or ts > t3:
        return 0.0
    if ts < t1:
        return smooth((ts - t0) / (t1 - t0))
    if ts < t2:
        return 1.0
    return 1.0 - smooth((ts - t2) / (t3 - t2))


def _pulse(ts, div=4.0):
    """0..1 beat-pulse at BPM/div."""
    return 0.5 + 0.5 * math.sin(2 * math.pi * (BPM / 60.0) / div * ts)


# --- background variants (animated) ---
def _bg_stars(ts):
    out = []
    for i in range(120):
        x = (i * 73 + 17) % W
        y = (i * 149 + 31 + int(ts * 6)) % H  # slow downward drift
        tw = 0.35 + 0.55 * (0.5 + 0.5 * math.sin(ts * 1.6 + i))
        out.append(f'<circle cx="{x}" cy="{y}" r="{0.7+(i%3)*0.5:.1f}" fill="#cfe9ee" opacity="{tw:.2f}"/>')
    return "".join(out)


def _bg_flow(ts):
    out = []
    for i in range(90):
        x = (i * 91 + 23) % W
        y = (i * 137 + 41) % H
        ang = math.sin(x * 0.006 + y * 0.004 + ts * 0.7) * math.pi
        ln = 46
        x2, y2 = x + ln * math.cos(ang), y + ln * math.sin(ang)
        out.append(f'<line x1="{x}" y1="{y}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="{V["a1"]}" stroke-width="1.4" opacity="0.14"/>')
    return "".join(out)


def _bg_grid(ts):
    out = []
    op = 0.05 + 0.05 * _pulse(ts)
    for gx in range(0, W + 1, 90):
        out.append(f'<line x1="{gx}" y1="0" x2="{gx}" y2="{H}" stroke="{V["a1"]}" stroke-width="1" opacity="{op:.3f}"/>')
    for gy in range(0, H + 1, 90):
        off = int(ts * 18) % 90
        out.append(f'<line x1="0" y1="{gy+off}" x2="{W}" y2="{gy+off}" stroke="{V["a1"]}" stroke-width="1" opacity="{op:.3f}"/>')
    return "".join(out)


def _background(ts):
    return {"stars": _bg_stars, "flow": _bg_flow, "grid": _bg_grid}[V["bg"]](ts)


def _scanlines():
    return "".join(f'<rect x="0" y="{y}" width="{W}" height="1" fill="#000" opacity="0.06"/>' for y in range(0, H, 4))


def _compass(cx, cy, r, ts, op):
    rot = ts * 16
    rays = []
    for i in range(8):
        a = math.radians(-90 + i * 45 + rot)
        col = V["a1"] if i % 2 == 0 else V["a2"]
        rays.append(f'<line x1="{cx}" y1="{cy}" x2="{cx+r*math.cos(a):.0f}" y2="{cy+r*math.sin(a):.0f}" stroke="{col}" stroke-width="3" opacity="{op*0.8:.2f}"/>')
    g = 0.7 + 0.3 * _pulse(ts)
    return (f'<g opacity="{op:.2f}">{"".join(rays)}'
            f'<circle cx="{cx}" cy="{cy}" r="{r*0.30:.0f}" fill="none" stroke="{V["a1"]}" stroke-width="4" filter="url(#glow)" opacity="{g:.2f}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r*0.12:.0f}" fill="{V["a1"]}" filter="url(#glow)"/></g>')


def _ring(cx, cy, r, ts, op):
    lit, focus, labels = BRIEF["lit"], BRIEF["focus"], BRIEF["labels"]
    pc = 0.55 + 0.45 * _pulse(ts)
    parts = [f'<circle cx="{cx}" cy="{cy}" r="{46+8*_pulse(ts):.0f}" fill="{V["a1"]}" opacity="0.22" filter="url(#big)"/>',
             f'<circle cx="{cx}" cy="{cy}" r="26" fill="{V["a1"]}" filter="url(#glow)"/>']
    for i in range(8):
        a = math.radians(-90 + i * 45)
        nx, ny = cx + r * math.cos(a), cy + r * math.sin(a)
        is_lit = i in lit or i == focus
        col = V["a1"] if i in lit else (V["a2"] if i == focus else DIM_AMBER)
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{nx:.0f}" y2="{ny:.0f}" stroke="{col}" stroke-width="2" opacity="{(0.5 if is_lit else 0.22):.2f}"/>')
        if is_lit:
            rad = 22 + (4 * pc if i == focus else 0)
            parts.append(f'<circle cx="{nx:.0f}" cy="{ny:.0f}" r="{rad:.0f}" fill="{col}" opacity="{(pc if i==focus else 0.95):.2f}" filter="url(#glow)"/>')
        else:
            parts.append(f'<circle cx="{nx:.0f}" cy="{ny:.0f}" r="20" fill="none" stroke="{DIM_AMBER}" stroke-width="2" opacity="0.55"/>')
        lx, ly = cx + (r + 58) * math.cos(a), cy + (r + 58) * math.sin(a)
        parts.append(f'<text x="{lx:.0f}" y="{ly:.0f}" font-family="{FONT}" font-size="26" fill="{col}" text-anchor="middle" opacity="{(0.9 if is_lit else 0.45):.2f}">{labels[i]}</text>')
    return f'<g opacity="{op:.2f}">{"".join(parts)}</g>'


def _umbra(cx, cy, sc, ts, op):
    breathe = 1.0 + 0.04 * math.sin(ts * 1.4)
    sc = sc * breathe
    blink = 1.0 if (ts % 3.4) > 0.12 else 0.15
    eye_r = 52 * blink * (1.0 + 0.10 * _pulse(ts))
    eye = V["eye"]
    runes = []
    for i in range(12):
        a = math.radians(i * 30 + ts * 12)
        rx, ry = cx + 150 * sc * math.cos(a), cy - 30 * sc + 150 * sc * math.sin(a)
        runes.append(f'<circle cx="{rx:.0f}" cy="{ry:.0f}" r="4" fill="{V["a1"] if i%2 else V["a2"]}" opacity="0.8" filter="url(#glow)"/>')
    return (f'<g opacity="{op:.2f}">'
            f'<ellipse cx="{cx}" cy="{cy+90*sc:.0f}" rx="{110*sc:.0f}" ry="{130*sc:.0f}" fill="url(#body)" stroke="#3a3f8a" stroke-width="2"/>'
            f'<ellipse cx="{cx}" cy="{cy-30*sc:.0f}" rx="{115*sc:.0f}" ry="{108*sc:.0f}" fill="url(#body)" stroke="#3a3f8a" stroke-width="2"/>'
            f'<path d="M{cx-70*sc:.0f},{cy-110*sc:.0f} L{cx-95*sc:.0f},{cy-175*sc:.0f} L{cx-40*sc:.0f},{cy-130*sc:.0f} Z" fill="url(#body)"/>'
            f'<path d="M{cx+70*sc:.0f},{cy-110*sc:.0f} L{cx+95*sc:.0f},{cy-175*sc:.0f} L{cx+40*sc:.0f},{cy-130*sc:.0f} Z" fill="url(#body)"/>'
            f'{"".join(runes)}'
            f'<circle cx="{cx}" cy="{cy-30*sc:.0f}" r="{eye_r*sc:.0f}" fill="{eye}" filter="url(#big)" opacity="0.9"/>'
            f'<circle cx="{cx}" cy="{cy-30*sc:.0f}" r="{eye_r*sc*0.6:.0f}" fill="url(#eye)"/>'
            f'<circle cx="{cx-14*sc:.0f}" cy="{cy-44*sc:.0f}" r="{10*sc:.0f}" fill="#eafffd" opacity="0.9"/>'
            f'</g>')


def _panel(text, col, op):
    return (f'<g opacity="{op:.2f}"><rect x="60" y="1600" width="960" height="92" fill="{VOID}" opacity="0.72"/>'
            f'<rect x="60" y="1600" width="6" height="92" fill="{col}"/>'
            f'<text x="92" y="1658" font-family="{FONT}" font-size="34" fill="{WHITE}">{esc(text)}</text></g>')


def _typed(text, x, y, ts, t0, col, size, op):
    n = max(0, int((ts - t0) * 22))
    cur = "_" if int(ts * 2) % 2 == 0 else " "
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{col}" opacity="{op:.2f}" filter="url(#glow)">{esc(text[:n])}{cur}</text>'


_CAM_KF = {
    "push": [(0,1.0,540,900),(5,1.05,540,760),(13,1.30,540,720),(23,1.36,540,900),(32,0.9,540,820),(45,0.9,540,820)],
    "pull": [(0,1.5,540,720),(5,1.4,540,740),(13,1.2,540,760),(23,1.0,540,860),(32,0.88,540,820),(45,0.85,540,820)],
    "drift":[(0,1.1,470,900),(5,1.12,540,760),(13,1.26,600,720),(23,1.3,500,920),(32,0.9,560,820),(45,0.9,520,820)],
}


def _camera(ts):
    kf = _CAM_KF[V["cam"]]
    s, fx, fy = kf[0][1], kf[0][2], kf[0][3]
    for i in range(len(kf) - 1):
        t0, s0, x0, y0 = kf[i]
        t1, s1, x1, y1 = kf[i + 1]
        if t0 <= ts <= t1:
            k = smooth((ts - t0) / (t1 - t0))
            s, fx, fy = s0+(s1-s0)*k, x0+(x1-x0)*k, y0+(y1-y0)*k
            break
    return f"translate({540-s*fx:.1f} {900-s*fy:.1f}) scale({s:.3f})"


CUTS = [13, 23, 32, 38]


def _glitch(ts):
    for c in CUTS:
        if 0 <= ts - c < 0.22:
            return (f'<g opacity="0.5"><rect x="0" y="{int(ts*90)%H}" width="{W}" height="40" fill="{V["a2"]}" opacity="0.14"/>'
                    f'<rect x="9" y="0" width="{W}" height="{H}" fill="{V["a1"]}" opacity="0.03"/></g>')
    return ""


def _defs():
    return ('<defs>'
            f'<radialGradient id="void" cx="50%" cy="42%" r="75%"><stop offset="0%" stop-color="#0a1018"/><stop offset="100%" stop-color="{VOID}"/></radialGradient>'
            f'<radialGradient id="eye" cx="50%" cy="45%" r="60%"><stop offset="0%" stop-color="#eafffd"/><stop offset="50%" stop-color="{V["eye"]}"/><stop offset="100%" stop-color="#0a3c40"/></radialGradient>'
            '<linearGradient id="body" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1c1840"/><stop offset="55%" stop-color="#0c0a22"/><stop offset="100%" stop-color="#040310"/></linearGradient>'
            '<radialGradient id="vign" cx="50%" cy="50%" r="72%"><stop offset="60%" stop-color="#000" stop-opacity="0"/><stop offset="100%" stop-color="#000" stop-opacity="0.7"/></radialGradient>'
            '<filter id="glow"><feGaussianBlur stdDeviation="4"/></filter>'
            '<filter id="big"><feGaussianBlur stdDeviation="20"/></filter>'
            '<filter id="soft"><feGaussianBlur stdDeviation="2"/></filter></defs>')


def _qr_scene(ts, op):
    qr = BRIEF.get("qr_png", "")
    img = (f'<image x="325" y="720" width="430" height="430" href="data:image/png;base64,{qr}"/>'
           if qr else '<rect x="325" y="720" width="430" height="430" fill="#fff"/>')
    return (f'<g opacity="{op:.2f}"><rect x="305" y="700" width="470" height="470" fill="#fff" rx="14"/>{img}'
            f'<text x="540" y="1260" font-family="{FONT}" font-size="40" fill="{V["a1"]}" text-anchor="middle">SUPPORT THE BUILD</text>'
            f'<text x="540" y="1320" font-family="{FONT}" font-size="26" fill="{MUTED}" text-anchor="middle">monobank</text>'
            f'<text x="540" y="1700" font-family="{FONT}" font-size="26" fill="{MUTED}" text-anchor="middle">github.com/umbraaeternaa/macbastion</text></g>')


def frame(ts):
    b = BRIEF
    world = (_compass(540, 760, 230, ts, fade(ts, 0.3, 1.5, 3.5, 5.5, 7.0))
             + _ring(540, 760, 300, ts, fade(ts, 4.5, 6.5, 24, 32, 38))
             + _umbra(540, 1150, 0.62, ts, fade(ts, 5.0, 7.0, 22, 30, 36)))
    screen = (f'<rect width="{W}" height="{H}" fill="url(#void)"/>' + _background(ts)
              + f'<g transform="{_camera(ts)}">{world}</g>')
    hud = _typed(f"> CHIMERA :: DAY {b['day']}", 90, 980, ts, 0.6, ACID, 46, fade(ts, 0.5, 1.2, 4.8, 5.8, 7.0))
    hud += _panel(b["event"], V["a1"], fade(ts, 13.5, 14.5, 21, 22.5, 23.5))
    hud += _panel("THE GATE — SEALED, NOT YET OPENED", AMBER, fade(ts, 24, 25, 30, 31.5, 32.5))
    tc = fade(ts, 32.5, 33.5, 36.5, 37, 38)
    hud += (f'<g opacity="{tc:.2f}" text-anchor="middle">'
            f'<text x="540" y="1380" font-family="{FONT}" font-size="64" fill="{WHITE}">DAY {b["day"]}</text>'
            f'<text x="540" y="1450" font-family="{FONT}" font-size="32" fill="{V["a1"]}">{esc(b["subtitle"])}</text>'
            f'<text x="540" y="1530" font-family="{FONT}" font-size="48" fill="{AMBER}">{b["modules_done"]} / 8</text>'
            f'<text x="540" y="1590" font-family="{FONT}" font-size="30" fill="{ACID}">{b["tests"]} TESTS GREEN</text></g>')
    hud += _qr_scene(ts, fade(ts, 38.5, 39.5, 44, 44.5, 45))
    overlay = _scanlines() + f'<rect width="{W}" height="{H}" fill="url(#vign)"/>' + _glitch(ts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'{_defs()}{screen}{hud}{overlay}</svg>')
