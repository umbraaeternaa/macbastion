#!/usr/bin/env python3
"""CHIMERA reel — SVG cinematic frame generator (maximalist daily-variation engine).

`frame(ts)` returns an SVG string for the whole timeline; render.py rasterises it via
cairosvg, then ffmpeg assembles (+grain +music). Style: cyberpunk x Interstellar x AI —
deep-space cosmos, an Interstellar black-hole core, a neural-net "mind" layer, an 8-module
arsenal ring with per-module glyphs + readouts, an operator HUD console (gauges, scope,
telemetry), the Umbra creature, heavy camera motion, glitch, a closing monobank QR card.

DAILY VARIATION (seed = brief["variant_seed"] or the day number): accent palette, camera
path and Umbra eye are chosen per day, so every reel is recognisably CHIMERA yet fresh.
MOTION: drifting parallax starfield, rotating galaxy + accretion disk, beat-pulse on
nodes/core/eye, travelling neural pulses, falling data streams, cut flashes, breathing
Umbra. Text = DejaVu Sans Mono (Menlo fallback).
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
_CAMS = ["push", "pull", "drift"]
_EYES = [TURQ, VIOLET, CYAN]


def _variant() -> dict:
    seed = BRIEF.get("variant_seed") or BRIEF.get("day", 0)
    r = random.Random(seed)
    a1, a2 = _SCHEMES[seed % len(_SCHEMES)]  # guaranteed daily colour rotation
    return {"a1": a1, "a2": a2, "cam": r.choice(_CAMS), "eye": r.choice(_EYES), "seed": seed}


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


def _beat(ts):
    """Sharp 0..1 spike on each beat (for flashes)."""
    ph = (ts * (BPM / 60.0)) % 1.0
    return math.exp(-ph * 7.0)


# --- deep-space cosmos (always-on base) -----------------------------------
def _nebula(ts):
    out = []
    for bx, by, br, gid, ph in [
        (300, 480, 540, "neb1", 0.0), (820, 1180, 620, "neb2", 0.5),
        (560, 1560, 500, "neb1", 0.3), (150, 1300, 440, "neb2", 0.8),
    ]:
        dx = 44 * math.sin(ts * 0.05 + ph * 6)
        dy = 30 * math.cos(ts * 0.04 + ph * 6)
        out.append(f'<ellipse cx="{bx+dx:.0f}" cy="{by+dy:.0f}" rx="{br}" ry="{br*0.82:.0f}" fill="url(#{gid})"/>')
    return "".join(out)


def _starfield(ts):
    out = []
    for li, (cnt, base, spd, sz) in enumerate([(70, 0.5, 5, 0.7), (60, 0.85, 11, 1.2), (40, 1.3, 20, 1.9)]):
        for i in range(cnt):
            x = (i * 97 + li * 43 + 17) % W
            y = (i * (151 + li * 7) + 31 + int(ts * spd * 4)) % H
            tw = base * (0.45 + 0.55 * (0.5 + 0.5 * math.sin(ts * 1.6 + i + li)))
            out.append(f'<circle cx="{x}" cy="{y}" r="{sz*0.42:.1f}" fill="#dff3f7" opacity="{tw:.2f}"/>')
    return "".join(out)


def _galaxy(ts):
    cx, cy, out, rot = 760, 430, [], ts * 0.06
    for i in range(120):
        t = i / 120
        ang = t * 6.0 * math.pi + rot + (i % 2) * math.pi
        rad = 26 + t * 540
        x, y = cx + rad * math.cos(ang), cy + rad * 0.6 * math.sin(ang)
        op = (1 - t) * 0.42
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{1.6*(1-t)+0.5:.1f}" fill="{V["a1"] if i%3 else "#dff3f7"}" opacity="{op:.2f}"/>')
    return "".join(out)


def _sakura(ts, op):
    """Drifting cherry-blossom petals — an anime signal layer (day-21 anime pass)."""
    out = []
    for i in range(28):
        sp = 24 + (i % 5) * 11
        x = (i * 79 + 40 + 22 * math.sin(ts * 0.5 + i)) % W
        y = (i * 131 + int(ts * sp)) % (H + 60) - 30
        rot = ts * 45 + i * 33
        pr = 7 + (i % 3) * 3
        col = "#ffffff" if i % 3 == 0 else ("#ffd1e8" if i % 3 == 1 else "#ffb3d9")
        out.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{pr}" ry="{pr*0.45:.0f}" fill="{col}" '
                   f'opacity="0.6" transform="rotate({rot:.0f} {x:.0f} {y:.0f})"/>')
    return f'<g opacity="{op:.2f}">{"".join(out)}</g>'


def _clouds(ts, op):
    """Soft anime cloud banks drifting across the sky."""
    out = []
    for cx0, cy, r, sp in [(260, 470, 300, 9), (840, 820, 360, 6), (520, 1520, 340, 12), (160, 1180, 240, 8)]:
        x = (cx0 + ts * sp) % (W + 760) - 380
        out.append(f'<ellipse cx="{x:.0f}" cy="{cy}" rx="{r}" ry="{r*0.42:.0f}" fill="#ffe9f4" '
                   f'opacity="0.07" filter="url(#big)"/>')
    return f'<g opacity="{op:.2f}">{"".join(out)}</g>'


def _cosmos(ts):
    return f'<g opacity="0.9">{_nebula(ts)}{_galaxy(ts)}{_starfield(ts)}</g>'


# --- Interstellar black-hole core -----------------------------------------
def _blackhole(cx, cy, r, ts, op):
    rot = ts * 38
    disk = (f'<ellipse cx="{cx}" cy="{cy}" rx="{r*2.0:.0f}" ry="{r*0.5:.0f}" fill="none" '
            f'stroke="url(#disk)" stroke-width="{r*0.42:.0f}" opacity="0.85" '
            f'transform="rotate({rot:.0f} {cx} {cy})" filter="url(#soft)"/>')
    halo = (f'<path d="M{cx-r*2.0:.0f},{cy} A{r*2.0:.0f},{r*2.0:.0f} 0 0 1 {cx+r*2.0:.0f},{cy}" '
            f'fill="none" stroke="url(#disk)" stroke-width="{r*0.26:.0f}" opacity="0.75" filter="url(#soft)"/>')
    ring = f'<circle cx="{cx}" cy="{cy}" r="{r*1.04:.0f}" fill="none" stroke="{AMBER}" stroke-width="3" opacity="{0.8+0.2*_pulse(ts):.2f}" filter="url(#glow)"/>'
    horizon = f'<circle cx="{cx}" cy="{cy}" r="{r:.0f}" fill="#000"/>'
    return f'<g opacity="{op:.2f}">{disk}{halo}{horizon}{ring}</g>'


# --- neural-net "mind" layer ----------------------------------------------
_NN_RNG = random.Random(777)
_NN_NODES = [(_NN_RNG.randint(70, 1010), _NN_RNG.randint(280, 1560)) for _ in range(24)]
_NN_EDGES = [(i, j) for i in range(24) for j in range(i + 1, 24)
             if (_NN_NODES[i][0]-_NN_NODES[j][0])**2 + (_NN_NODES[i][1]-_NN_NODES[j][1])**2 < 280**2]


def _neural(ts, op):
    out = []
    for i, j in _NN_EDGES:
        x1, y1 = _NN_NODES[i]; x2, y2 = _NN_NODES[j]
        out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{V["a2"]}" stroke-width="1" opacity="0.09"/>')
    for k, (i, j) in enumerate(_NN_EDGES[::2]):
        x1, y1 = _NN_NODES[i]; x2, y2 = _NN_NODES[j]
        f = ((ts * 0.45 + k * 0.17) % 1.0)
        px, py = x1 + (x2 - x1) * f, y1 + (y2 - y1) * f
        out.append(f'<circle cx="{px:.0f}" cy="{py:.0f}" r="2.6" fill="{V["a1"]}" opacity="0.65" filter="url(#glow)"/>')
    for x, y in _NN_NODES:
        tw = 0.35 + 0.4 * (0.5 + 0.5 * math.sin(ts * 2 + x * 0.01))
        out.append(f'<circle cx="{x}" cy="{y}" r="3.4" fill="{V["a1"]}" opacity="{tw:.2f}"/>')
    return f'<g opacity="{op:.2f}">{"".join(out)}</g>'


# --- falling data streams --------------------------------------------------
_GLY = "0123456789ABCDEF#/<>x="


def _datastream(ts, op):
    out = []
    for c in range(14):
        x = 46 + c * 76
        speed = 70 + (c % 5) * 30
        head = int(ts * speed) % (H + 280) - 120
        for k in range(8):
            y = head - k * 32
            if 0 < y < H:
                ch = _GLY[(c * 7 + k + int(ts * 8)) % len(_GLY)]
                o = max(0.0, 0.5 - k * 0.06) * 0.55
                out.append(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="20" fill="{V["a1"]}" opacity="{o:.2f}">{esc(ch)}</text>')
    return f'<g opacity="{op:.2f}">{"".join(out)}</g>'


# --- quantum interference backdrop (day 13: wave physics) -----------------
def _quantum(ts, op):
    out = []
    for sx, sy, ph in [(320, 560, 0.0), (770, 1120, math.pi), (540, 1620, math.pi / 2)]:
        for k in range(8):
            rr = (ts * 58 + k * 64 + ph * 26) % 520
            o = max(0.0, 1 - rr / 520) * 0.13
            col = V["a2"] if (k % 2) else V["a1"]
            out.append(f'<circle cx="{sx}" cy="{sy}" r="{rr:.0f}" fill="none" stroke="{col}" stroke-width="1.3" opacity="{o:.2f}"/>')
    return f'<g opacity="{op:.2f}">{"".join(out)}</g>'


# --- heartbeat pulse: the organism breathes (day 13) ----------------------
def _heartbeat(cx, cy, r, ts, op):
    out = []
    for k in range(3):
        ph = (ts * (BPM / 60.0) * 0.5 + k / 3.0) % 1.0
        rr = r * (0.28 + ph * 1.35)
        o = max(0.0, 1 - ph) * 0.5
        out.append(f'<circle cx="{cx}" cy="{cy}" r="{rr:.0f}" fill="none" stroke="{V["a2"]}" '
                   f'stroke-width="{3*(1-ph)+1:.1f}" opacity="{o:.2f}" filter="url(#glow)"/>')
    return f'<g opacity="{op:.2f}">{"".join(out)}</g>'


# --- operator HUD console (instruments) -----------------------------------
def _gauge(cx, cy, r, frac, col, label, ts):
    a0, a1 = math.radians(135), math.radians(135 + 270 * max(0.0, min(1.0, frac)))
    x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
    x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
    track = (f'<path d="M{cx+r*math.cos(math.radians(135)):.0f},{cy+r*math.sin(math.radians(135)):.0f} '
             f'A{r},{r} 0 1 1 {cx+r*math.cos(math.radians(45)):.0f},{cy+r*math.sin(math.radians(45)):.0f}" '
             f'fill="none" stroke="{MUTED}" stroke-width="3" opacity="0.4"/>')
    large = 1 if (a1 - a0) > math.pi else 0
    arc = f'<path d="M{x0:.0f},{y0:.0f} A{r},{r} 0 {large} 1 {x1:.0f},{y1:.0f}" fill="none" stroke="{col}" stroke-width="4" opacity="0.9" filter="url(#glow)"/>'
    nd = f'<circle cx="{x1:.0f}" cy="{y1:.0f}" r="4" fill="{col}"/>'
    txt = f'<text x="{cx}" y="{cy+5}" font-family="{FONT}" font-size="20" fill="{WHITE}" text-anchor="middle">{label}</text>'
    return track + arc + nd + txt


def _hud(ts, op):
    px = int((ts * 53) % 4096)
    threat = int(2 + 2 * _pulse(ts, 8))
    tele = [
        f"CORE 0x{px:04X}", f"MODE  NOMINAL", f"THREAT {'#'*threat}{'.'*(5-threat)}",
        f"NET   {int(40+30*_pulse(ts,6))}MB/S",
    ]
    lines = "".join(
        f'<text x="60" y="{150+k*30}" font-family="{FONT}" font-size="22" fill="{V["a1"]}" opacity="0.85">{esc(t)}</text>'
        for k, t in enumerate(tele))
    pts = " ".join(f"{60+i*4:.0f},{300+18*math.sin(i*0.18+ts*5)*(0.5+0.5*_pulse(ts)):.0f}" for i in range(0, 110))
    scope = f'<polyline points="{pts}" fill="none" stroke="{V["a2"]}" stroke-width="2" opacity="0.7"/>'
    g1 = _gauge(960, 180, 52, _pulse(ts, 6), V["a1"], "LD", ts)
    g2 = _gauge(960, 320, 40, _pulse(ts, 3), V["a2"], "IO", ts)
    br = []
    for bx, by, sx, sy in [(34, 110, 1, 1), (1046, 110, -1, 1), (34, 1810, 1, -1), (1046, 1810, -1, -1)]:
        br.append(f'<path d="M{bx},{by+34*sy} V{by} H{bx+34*sx}" fill="none" stroke="{V["a1"]}" stroke-width="3" opacity="0.6"/>')
    return f'<g opacity="{op:.2f}">{"".join(br)}{lines}{scope}{g1}{g2}</g>'


# --- module glyphs (the arsenal) ------------------------------------------
def _glyph(i, x, y, s, col):
    a = f'stroke="{col}" stroke-width="2.4" fill="none"'
    if i == 0:  # CHAFF — scatter/noise
        return "".join(f'<circle cx="{x+dx:.0f}" cy="{y+dy:.0f}" r="2.4" fill="{col}"/>'
                       for dx, dy in [(-s, -s*0.4), (s*0.5, -s*0.6), (-s*0.3, s*0.5), (s*0.7, s*0.3), (0, 0)])
    if i == 1:  # ECHO — equalizer bars
        return "".join(f'<rect x="{x-s+k*s*0.75:.0f}" y="{y-h:.0f}" width="{s*0.4:.0f}" height="{2*h:.0f}" fill="{col}"/>'
                       for k, h in enumerate([s*0.5, s, s*0.7]))
    if i == 2:  # ORACLE — eye
        return f'<circle cx="{x}" cy="{y}" r="{s}" {a}/><circle cx="{x}" cy="{y}" r="{s*0.4:.0f}" fill="{col}"/>'
    if i == 3:  # MIRROR — mirrored triangles
        return (f'<path d="M{x-s:.0f},{y+s*0.6:.0f} L{x:.0f},{y-s*0.6:.0f} L{x:.0f},{y+s*0.6:.0f} Z" fill="{col}" opacity="0.85"/>'
                f'<path d="M{x+s:.0f},{y+s*0.6:.0f} L{x:.0f},{y-s*0.6:.0f} L{x:.0f},{y+s*0.6:.0f} Z" fill="{col}" opacity="0.45"/>')
    if i == 4:  # PULSE — ECG
        return f'<polyline points="{x-s:.0f},{y} {x-s*0.4:.0f},{y} {x-s*0.1:.0f},{y-s:.0f} {x+s*0.2:.0f},{y+s:.0f} {x+s*0.5:.0f},{y} {x+s:.0f},{y}" {a}/>'
    if i == 5:  # VAULT — padlock
        return (f'<rect x="{x-s*0.7:.0f}" y="{y-s*0.1:.0f}" width="{s*1.4:.0f}" height="{s:.0f}" rx="2" fill="{col}"/>'
                f'<path d="M{x-s*0.4:.0f},{y-s*0.1:.0f} v{-s*0.4:.0f} a{s*0.4:.0f},{s*0.4:.0f} 0 0 1 {s*0.8:.0f},0 v{s*0.4:.0f}" {a}/>')
    if i == 6:  # TETHER — link
        return f'<circle cx="{x-s*0.45:.0f}" cy="{y}" r="{s*0.5:.0f}" {a}/><circle cx="{x+s*0.45:.0f}" cy="{y}" r="{s*0.5:.0f}" {a}/>'
    return f'<path d="M{x-s:.0f},{y-s:.0f} L{x+s:.0f},{y+s:.0f} M{x+s:.0f},{y-s:.0f} L{x-s:.0f},{y+s:.0f}" {a}/>'  # PURGE — X


def _compass(cx, cy, r, ts, op):
    rot = ts * 16
    rays = []
    for i in range(8):
        ang = math.radians(-90 + i * 45 + rot)
        col = V["a1"] if i % 2 == 0 else V["a2"]
        rays.append(f'<line x1="{cx}" y1="{cy}" x2="{cx+r*math.cos(ang):.0f}" y2="{cy+r*math.sin(ang):.0f}" stroke="{col}" stroke-width="3" opacity="{op*0.8:.2f}"/>')
    g = 0.7 + 0.3 * _pulse(ts)
    return (f'<g opacity="{op:.2f}">{"".join(rays)}'
            f'<circle cx="{cx}" cy="{cy}" r="{r*0.30:.0f}" fill="none" stroke="{V["a1"]}" stroke-width="4" filter="url(#glow)" opacity="{g:.2f}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r*0.12:.0f}" fill="{V["a1"]}" filter="url(#glow)"/></g>')


def _ring(cx, cy, r, ts, op):
    lit, labels = BRIEF["lit"], BRIEF["labels"]
    fr = BRIEF["focus"]
    focuses = fr if isinstance(fr, list) else [fr]
    pc = 0.55 + 0.45 * _pulse(ts)
    spin = ts * 6  # the arsenal slowly rotates
    parts = []
    for ridx in range(2):  # twin orbit rings
        rr = r + ridx * 26
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{rr:.0f}" fill="none" stroke="{V["a1"]}" stroke-width="1" opacity="{0.10+0.05*ridx:.2f}"/>')
    for i in range(8):
        a = math.radians(-90 + i * 45 + spin)
        nx, ny = cx + r * math.cos(a), cy + r * math.sin(a)
        is_focus = i in focuses
        is_lit = i in lit or is_focus
        col = V["a2"] if is_focus else (V["a1"] if i in lit else DIM_AMBER)
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{nx:.0f}" y2="{ny:.0f}" stroke="{col}" stroke-width="2" opacity="{(0.45 if is_lit else 0.18):.2f}"/>')
        rad = 30 + (5 * pc if is_focus else 0)
        if is_lit:
            parts.append(f'<circle cx="{nx:.0f}" cy="{ny:.0f}" r="{rad+2:.0f}" fill="{VOID}" stroke="#0a0618" stroke-width="5" opacity="0.9"/>')
            parts.append(f'<circle cx="{nx:.0f}" cy="{ny:.0f}" r="{rad:.0f}" fill="{VOID}" stroke="{col}" stroke-width="2.5" opacity="0.95" filter="url(#glow)"/>')
            parts.append(f'<circle cx="{nx:.0f}" cy="{ny:.0f}" r="{rad+6:.0f}" fill="none" stroke="{col}" stroke-width="1" opacity="{(pc if is_focus else 0.5):.2f}"/>')
        else:
            parts.append(f'<circle cx="{nx:.0f}" cy="{ny:.0f}" r="26" fill="{VOID}" stroke="{DIM_AMBER}" stroke-width="2" opacity="0.6"/>')
        if is_focus:  # day-13 register handshake: a packet travels node -> core
            hf = (ts * 0.8 + i * 0.37) % 1.0
            hx, hy = nx + (cx - nx) * hf, ny + (cy - ny) * hf
            parts.append(f'<circle cx="{hx:.0f}" cy="{hy:.0f}" r="5" fill="{V["a2"]}" opacity="{(1-hf)*0.9:.2f}" filter="url(#glow)"/>')
            # day-15 VAULT motif: a time-lock dial — a 12-tick ring + a sweeping relock hand —
            # plus an OPEN/decrypt return packet (core -> node), closing the seal<->open round-trip.
            dial_r = rad + 14
            for t in range(12):
                ta = math.radians(t * 30 + ts * 12)
                tx1, ty1 = nx + dial_r * math.cos(ta), ny + dial_r * math.sin(ta)
                tx2, ty2 = nx + (dial_r + 7) * math.cos(ta), ny + (dial_r + 7) * math.sin(ta)
                parts.append(f'<line x1="{tx1:.0f}" y1="{ty1:.0f}" x2="{tx2:.0f}" y2="{ty2:.0f}" stroke="{V["a2"]}" stroke-width="1.5" opacity="0.5"/>')
            ha = math.radians(-90 + (ts * 60) % 360)  # the relock hand sweeps once / 6s
            parts.append(f'<line x1="{nx:.0f}" y1="{ny:.0f}" x2="{nx + dial_r * math.cos(ha):.0f}" y2="{ny + dial_r * math.sin(ha):.0f}" stroke="{V["a2"]}" stroke-width="2" opacity="0.85" filter="url(#glow)"/>')
            of = (ts * 0.8 + i * 0.37 + 0.5) % 1.0  # the OPEN/decrypt return packet: core -> node
            ox, oy = cx + (nx - cx) * of, cy + (ny - cy) * of
            parts.append(f'<circle cx="{ox:.0f}" cy="{oy:.0f}" r="4" fill="{ACID}" opacity="{(1-of)*0.85:.2f}" filter="url(#glow)"/>')
        parts.append(_glyph(i, nx, ny, 13, col))
        lx, ly = cx + (r + 64) * math.cos(a), cy + (r + 64) * math.sin(a)
        parts.append(f'<text x="{lx:.0f}" y="{ly:.0f}" font-family="{FONT}" font-size="24" fill="{col}" text-anchor="middle" opacity="{(0.9 if is_lit else 0.4):.2f}">{labels[i]}</text>')
        if is_lit:
            parts.append(f'<text x="{lx:.0f}" y="{ly+22:.0f}" font-family="{FONT}" font-size="15" fill="{V["a2"] if is_focus else ACID}" text-anchor="middle" opacity="0.8">{"LIVE" if is_focus else "ONLINE"}</text>')
    return f'<g opacity="{op:.2f}">{"".join(parts)}</g>'


def _umbra(cx, cy, sc, ts, op):
    sc = sc * (1.0 + 0.04 * math.sin(ts * 1.4))
    blink = 1.0 if (ts % 3.4) > 0.12 else 0.15
    eye_r = 52 * blink * (1.0 + 0.10 * _pulse(ts))
    eye = V["eye"]
    runes = []
    for i in range(14):
        a = math.radians(i * (360 / 14) + ts * 12)
        rad = 150 + 14 * math.sin(ts * 2 + i)
        rx, ry = cx + rad * sc * math.cos(a), cy - 30 * sc + rad * sc * math.sin(a)
        runes.append(f'<circle cx="{rx:.0f}" cy="{ry:.0f}" r="4" fill="{V["a1"] if i%2 else V["a2"]}" opacity="0.8" filter="url(#glow)"/>')
    return (f'<g opacity="{op:.2f}">'
            f'<ellipse cx="{cx}" cy="{cy+90*sc:.0f}" rx="{110*sc:.0f}" ry="{130*sc:.0f}" fill="url(#body)" stroke="#160a2e" stroke-width="4"/>'
            f'<ellipse cx="{cx}" cy="{cy-30*sc:.0f}" rx="{115*sc:.0f}" ry="{108*sc:.0f}" fill="url(#body)" stroke="#160a2e" stroke-width="4"/>'
            f'<path d="M{cx-70*sc:.0f},{cy-110*sc:.0f} L{cx-95*sc:.0f},{cy-175*sc:.0f} L{cx-40*sc:.0f},{cy-130*sc:.0f} Z" fill="url(#body)"/>'
            f'<path d="M{cx+70*sc:.0f},{cy-110*sc:.0f} L{cx+95*sc:.0f},{cy-175*sc:.0f} L{cx+40*sc:.0f},{cy-130*sc:.0f} Z" fill="url(#body)"/>'
            f'{"".join(runes)}'
            f'<circle cx="{cx}" cy="{cy-30*sc:.0f}" r="{eye_r*sc:.0f}" fill="{eye}" filter="url(#big)" opacity="0.9"/>'
            f'<circle cx="{cx}" cy="{cy-30*sc:.0f}" r="{eye_r*sc*0.62:.0f}" fill="url(#eye)" stroke="#10081f" stroke-width="{3.5*sc:.1f}"/>'
            f'<circle cx="{cx-14*sc:.0f}" cy="{cy-44*sc:.0f}" r="{11*sc:.0f}" fill="#eafffd" opacity="0.95"/>'
            f'<circle cx="{cx+9*sc:.0f}" cy="{cy-20*sc:.0f}" r="{5*sc:.0f}" fill="#ffffff" opacity="0.85"/>'
            f'</g>')


def _panel(text, col, op):
    return (f'<g opacity="{op:.2f}"><rect x="60" y="1600" width="960" height="92" fill="{VOID}" opacity="0.72"/>'
            f'<rect x="60" y="1600" width="6" height="92" fill="{col}"/>'
            f'<text x="92" y="1658" font-family="{FONT}" font-size="34" fill="{WHITE}">{esc(text)}</text></g>')


# --- NEW day-16 motif: the reflex audit ledger (a live log of what the one mind did) ---
_LEDGER = [
    ("tether.absent -> vault.lock", "ok"),
    ("anomaly -> chaff + echo", "ok"),
    ("pulse exhausted -> vault.lock", "ok"),
    ("tether.recovered -> stand down", "ok"),
    ("escalation L3 -> purge", "refused"),
]


def _ledger(ts, op):
    """A terminal panel that reveals real reflex actuations one by one — the
    `chimera audit` trail, made visual (today's build). Each line types in like a
    live log; the refused L3 PURGE is amber (security-relevant)."""
    if op <= 0.02:
        return ""
    x, y0 = 300, 1392
    blink = "_" if int(ts * 2) % 2 == 0 else " "
    back = (f'<rect x="{x-18}" y="{y0-34}" width="520" height="206" rx="7" fill="{VOID}" opacity="0.6"/>'
            f'<rect x="{x-18}" y="{y0-34}" width="5" height="206" fill="{ACID}" opacity="0.85"/>')
    head = (f'<circle cx="{x}" cy="{y0-9}" r="5" fill="{ACID}" opacity="{0.5+0.5*_pulse(ts,3):.2f}"/>'
            f'<text x="{x+18}" y="{y0}" font-family="{FONT}" font-size="22" fill="{ACID}">AUDIT TRAIL ::</text>')
    rows, last = [], -1
    for k, (txt, tag) in enumerate(_LEDGER):
        rv = max(0.0, min(1.0, (ts - (16.0 + k * 0.85)) * 2.4))
        if rv <= 0.02:
            continue
        last = k
        ly = y0 + 36 + k * 30
        col = AMBER if tag == "refused" else (V["a1"] if k % 2 == 0 else V["a2"])
        rows.append(f'<text x="{x}" y="{ly:.0f}" font-family="{FONT}" font-size="20" '
                    f'fill="{col}" opacity="{rv*0.95:.2f}">{esc(txt + "  [" + tag + "]")}</text>')
    if 0 <= last < len(_LEDGER):
        cy = y0 + 36 + last * 30
        rows.append(f'<text x="{x+486}" y="{cy:.0f}" font-family="{FONT}" font-size="20" '
                    f'fill="{ACID}" text-anchor="end">{blink}</text>')
    return f'<g opacity="{op:.2f}">{back}{head}{"".join(rows)}</g>'


def _typed(text, x, y, ts, t0, col, size, op):
    n = max(0, int((ts - t0) * 22))
    cur = "_" if int(ts * 2) % 2 == 0 else " "
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{col}" opacity="{op:.2f}" filter="url(#glow)">{esc(text[:n])}{cur}</text>'


_CAM_KF = {
    "push": [(0,1.0,540,820),(5,1.10,540,760),(13,1.34,540,720),(23,1.40,540,900),(32,0.92,540,820),(45,0.92,540,820)],
    "pull": [(0,1.55,540,720),(5,1.42,540,740),(13,1.22,540,760),(23,1.02,540,860),(32,0.88,540,820),(45,0.86,540,820)],
    "drift":[(0,1.12,470,900),(5,1.16,560,760),(13,1.30,610,720),(23,1.32,490,920),(32,0.92,560,820),(45,0.92,520,820)],
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
    shake = 5.0 * _beat(ts) * (1.0 if 12 < ts < 33 else 0.3)
    return f"translate({540-s*fx+math.sin(ts*40)*shake:.1f} {900-s*fy:.1f}) scale({s:.3f})"


CUTS = [5, 13, 18, 23, 32, 38]


def _glitch(ts):
    for c in CUTS:
        if 0 <= ts - c < 0.20:
            yy = int(ts * 120) % H
            return (f'<g><rect x="0" y="{yy}" width="{W}" height="46" fill="{V["a2"]}" opacity="0.16"/>'
                    f'<rect x="-7" y="0" width="{W}" height="{H}" fill="{V["a1"]}" opacity="0.05"/>'
                    f'<rect x="7" y="0" width="{W}" height="{H}" fill="{V["a2"]}" opacity="0.05"/></g>')
    f = _beat(ts)
    if f > 0.6:
        return f'<rect width="{W}" height="{H}" fill="{V["a1"]}" opacity="{(f-0.6)*0.08:.3f}"/>'
    return ""


def _defs():
    return ('<defs>'
            f'<radialGradient id="void" cx="50%" cy="42%" r="80%"><stop offset="0%" stop-color="#0a1018"/><stop offset="100%" stop-color="{VOID}"/></radialGradient>'
            '<linearGradient id="sky" x1="0" y1="0" x2="0.2" y2="1"><stop offset="0%" stop-color="#160b38"/><stop offset="40%" stop-color="#3a1a63"/><stop offset="72%" stop-color="#5e2270"/><stop offset="100%" stop-color="#7d2a5a"/></linearGradient>'
            f'<radialGradient id="neb1" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="{V["a1"]}" stop-opacity="0.20"/><stop offset="65%" stop-color="{V["a1"]}" stop-opacity="0.05"/><stop offset="100%" stop-color="{V["a1"]}" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="neb2" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="{V["a2"]}" stop-opacity="0.18"/><stop offset="65%" stop-color="{V["a2"]}" stop-opacity="0.05"/><stop offset="100%" stop-color="{V["a2"]}" stop-opacity="0"/></radialGradient>'
            f'<linearGradient id="disk" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="{V["a2"]}"/><stop offset="50%" stop-color="{AMBER}"/><stop offset="100%" stop-color="{V["a1"]}"/></linearGradient>'
            f'<radialGradient id="eye" cx="50%" cy="45%" r="60%"><stop offset="0%" stop-color="#eafffd"/><stop offset="50%" stop-color="{V["eye"]}"/><stop offset="100%" stop-color="#0a3c40"/></radialGradient>'
            '<linearGradient id="body" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1c1840"/><stop offset="55%" stop-color="#0c0a22"/><stop offset="100%" stop-color="#040310"/></linearGradient>'
            '<radialGradient id="vign" cx="50%" cy="50%" r="74%"><stop offset="58%" stop-color="#000" stop-opacity="0"/><stop offset="100%" stop-color="#000" stop-opacity="0.72"/></radialGradient>'
            '<filter id="glow"><feGaussianBlur stdDeviation="4"/></filter>'
            '<filter id="big"><feGaussianBlur stdDeviation="20"/></filter>'
            '<filter id="soft"><feGaussianBlur stdDeviation="3"/></filter></defs>')


def _qr_scene(ts, op):
    qr = BRIEF.get("qr_png", "")
    img = (f'<image x="325" y="720" width="430" height="430" href="data:image/png;base64,{qr}"/>'
           if qr else '<rect x="325" y="720" width="430" height="430" fill="#fff"/>')
    return (f'<g opacity="{op:.2f}"><rect x="305" y="700" width="470" height="470" fill="#fff" rx="14"/>{img}'
            f'<text x="540" y="1260" font-family="{FONT}" font-size="40" fill="{V["a1"]}" text-anchor="middle">SUPPORT THE BUILD</text>'
            f'<text x="540" y="1320" font-family="{FONT}" font-size="26" fill="{MUTED}" text-anchor="middle">monobank</text>'
            f'<text x="540" y="1700" font-family="{FONT}" font-size="26" fill="{MUTED}" text-anchor="middle">github.com/umbraaeternaa/macbastion</text></g>')


# --- attestation gate (day 14: the signed core passes, a same-uid impostor bounces) ---
def _attest(cx, cy, ts, op):
    if op <= 0.01:
        return ""
    out = []
    gate_r = 205
    bp = _pulse(ts, 2.0)
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{gate_r}" fill="none" stroke="{V["a2"]}" '
               f'stroke-width="{1.5 + bp:.1f}" stroke-dasharray="5 11" opacity="0.5"/>')
    period, spawn = 3.4, 440
    for idx, (ang, signed) in enumerate(((-32.0, True), (148.0, False))):
        ph = (ts / period + idx * 0.5) % 1.0
        a = math.radians(ang)
        if signed:  # the signed core: cleared, travels all the way to the core
            d = spawn * (1.0 - ph)
            col, glyph = ACID, "✓"
        else:  # same-uid impostor: hits the gate at mid-phase, bounces back out
            d = (spawn - (spawn - gate_r) * (ph / 0.5)) if ph < 0.5 \
                else (gate_r + (spawn - gate_r) * ((ph - 0.5) / 0.5))
            col, glyph = "#ff4d6d", "✗"
        px, py = cx + d * math.cos(a), cy + d * math.sin(a)
        out.append(f'<circle cx="{px:.0f}" cy="{py:.0f}" r="9" fill="{col}" opacity="0.92" filter="url(#glow)"/>')
        out.append(f'<text x="{px:.0f}" y="{py - 15:.0f}" font-family="{FONT}" font-size="24" '
                   f'fill="{col}" text-anchor="middle" opacity="0.95">{glyph}</text>')
        if (not signed) and 0.46 < ph < 0.58:  # reject flash at the gate
            gx, gy = cx + gate_r * math.cos(a), cy + gate_r * math.sin(a)
            out.append(f'<circle cx="{gx:.0f}" cy="{gy:.0f}" r="{18 + 250 * (ph - 0.46):.0f}" '
                       f'fill="none" stroke="{col}" stroke-width="2" opacity="{max(0.0, 0.8 - 6.6 * (ph - 0.46)):.2f}"/>')
    out.append(f'<text x="{cx}" y="{cy - gate_r - 18:.0f}" font-family="{FONT}" font-size="21" '
               f'fill="{V["a1"]}" text-anchor="middle" opacity="0.85">ATTEST :: SIG ✓ / ✗</text>')
    return f'<g opacity="{op:.2f}">{"".join(out)}</g>'


def _jitter(ts, op):
    """MIRROR (day 17): the injected behavioural-noise trace — a humanlike jittered
    input signal that FLATTENS inside a SECURE window (a lock-marked field), exactly the
    secure-field downgrade shipped today: full noise everywhere, light over secrets."""
    if op <= 0.01:
        return ""
    x0, x1, y0 = 150, 930, 1300
    sec_a, sec_b = 510, 660  # the secure-field window: jitter collapses to "light" here

    def _amp(x):
        return 3.0 if sec_a < x < sec_b else 34.0

    def _noise(x):  # layered sines = Gaussian-ish humanlike jitter, animated by ts
        return (math.sin(x * 0.06 + ts * 5.0)
                + math.sin(x * 0.17 + ts * 8.0) * 0.5
                + math.sin(x * 0.31 + ts * 11.0) * 0.3)

    pts = []
    for i in range(131):
        x = x0 + (x1 - x0) * i / 130.0
        pts.append(f"{x:.0f},{y0 + _noise(x) * _amp(x) / 1.8:.0f}")
    # a dark instrument backing lifts the trace off the dense scene behind it
    back = (f'<rect x="{x0-34}" y="{y0-104}" width="{x1-x0+68}" height="196" rx="12" '
            f'fill="{VOID}" opacity="0.62"/>'
            f'<rect x="{x0-34}" y="{y0-104}" width="{x1-x0+68}" height="196" rx="12" '
            f'fill="none" stroke="{V["a1"]}" stroke-width="1.4" opacity="0.35"/>')
    trace = (f'<polyline points="{" ".join(pts)}" fill="none" stroke="{V["a1"]}" '
             f'stroke-width="2.5" opacity="0.95" filter="url(#glow)"/>')
    midx = (sec_a + sec_b) // 2
    band = (f'<rect x="{sec_a}" y="{y0-46}" width="{sec_b-sec_a}" height="92" rx="6" fill="{ACID}" opacity="0.08"/>'
            f'<rect x="{sec_a}" y="{y0-46}" width="{sec_b-sec_a}" height="92" rx="6" fill="none" '
            f'stroke="{ACID}" stroke-width="1.5" opacity="0.5"/>')
    lock = (f'<g opacity="0.9" filter="url(#glow)">'
            f'<rect x="{midx-11}" y="{y0-88}" width="22" height="17" rx="3" fill="none" stroke="{ACID}" stroke-width="2.5"/>'
            f'<path d="M{midx-7},{y0-88} v-6 a7,7 0 0 1 14,0 v6" fill="none" stroke="{ACID}" stroke-width="2.5"/></g>')
    cx = x0 + (x1 - x0) * ((ts * 0.17) % 1.0)
    cur = (f'<circle cx="{cx:.0f}" cy="{y0 + _noise(cx) * _amp(cx) / 1.8:.0f}" r="6" '
           f'fill="{V["a2"]}" filter="url(#glow)"/>')
    labs = (f'<text x="{x0}" y="{y0-58}" font-family="{FONT}" font-size="20" fill="{V["a1"]}" opacity="0.8">INPUT JITTER</text>'
            f'<text x="{midx}" y="{y0+74}" font-family="{FONT}" font-size="18" fill="{ACID}" text-anchor="middle" opacity="0.85">SECURE · LIGHT</text>')
    return f'<g opacity="{op:.2f}">{back}{band}{trace}{lock}{cur}{labs}</g>'


def _pulse_meter(ts, op):
    """PULSE (day 18): the operator-fatigue meter. Three senses — idle, input dynamics,
    behavioural drift — feed a cognitive-load bar that rises and crosses the
    NORMAL/CAUTION/TIRED/EXHAUSTED gates, its colour climbing green->amber->red. Exactly
    what PULSE now does live: it senses the operator and the gate adds friction."""
    if op <= 0.01:
        return ""
    x0, x1, y = 180, 900, 1316
    w = x1 - x0
    back = (f'<rect x="{x0-40}" y="{y-118}" width="{w+80}" height="208" rx="12" fill="{VOID}" opacity="0.62"/>'
            f'<rect x="{x0-40}" y="{y-118}" width="{w+80}" height="208" rx="12" fill="none" '
            f'stroke="{V["a1"]}" stroke-width="1.4" opacity="0.35"/>')
    level = max(0.0, min(0.92, 0.92 * smooth((ts - 10.0) / 4.6)))  # fatigue climbs as senses feed
    col = ACID if level < 0.4 else (AMBER if level < 0.7 else (MAGENTA if level < 0.9 else "#FF2D55"))
    mode = ("NORMAL" if level < 0.4 else
            ("CAUTION" if level < 0.7 else ("TIRED" if level < 0.9 else "EXHAUSTED")))
    title = (f'<text x="{x0}" y="{y-86}" font-family="{FONT}" font-size="20" fill="{V["a1"]}" opacity="0.85">OPERATOR FATIGUE</text>'
             f'<text x="{x1}" y="{y-86}" font-family="{FONT}" font-size="22" fill="{col}" text-anchor="end" filter="url(#glow)">{mode}</text>')
    feeds = []
    for i, lab in enumerate(("IDLE", "INPUT", "DRIFT")):
        fx = x0 + w * (0.2 + 0.3 * i)
        pu = 0.4 + 0.6 * _pulse(ts, 2 + i)
        feeds.append(f'<circle cx="{fx:.0f}" cy="{y-56}" r="{5+3*pu:.0f}" fill="{V["a2"]}" opacity="{pu:.2f}" filter="url(#glow)"/>')
        feeds.append(f'<line x1="{fx:.0f}" y1="{y-50}" x2="{fx:.0f}" y2="{y}" stroke="{V["a2"]}" stroke-width="1.5" opacity="{0.35*pu:.2f}"/>')
        feeds.append(f'<text x="{fx:.0f}" y="{y-70}" font-family="{FONT}" font-size="15" fill="{V["a1"]}" text-anchor="middle" opacity="0.8">{lab}</text>')
    track = f'<rect x="{x0}" y="{y}" width="{w}" height="26" rx="13" fill="{MUTED}" opacity="0.25"/>'
    fill = f'<rect x="{x0}" y="{y}" width="{w*level:.0f}" height="26" rx="13" fill="{col}" opacity="0.92" filter="url(#glow)"/>'
    ticks = []
    for frac, lab in ((0.4, "CAUTION"), (0.7, "TIRED"), (0.9, "EXH")):
        tx = x0 + w * frac
        ticks.append(f'<line x1="{tx:.0f}" y1="{y-6}" x2="{tx:.0f}" y2="{y+32}" stroke="{WHITE}" stroke-width="1.5" opacity="0.5"/>')
        ticks.append(f'<text x="{tx:.0f}" y="{y+50}" font-family="{FONT}" font-size="15" fill="{MUTED}" text-anchor="middle">{lab}</text>')
    return f'<g opacity="{op:.2f}">{back}{title}{"".join(feeds)}{track}{fill}{"".join(ticks)}</g>'


def frame(ts):
    b = BRIEF
    # central core: an Interstellar black hole that opens, then shrinks to the ring core
    bh_r = 150 - 110 * smooth((ts - 6) / 9) if ts < 15 else 40
    bh_op = fade(ts, 5.0, 7.0, 30, 33, 35)
    world = (_blackhole(540, 760, max(34, bh_r), ts, bh_op)
             + _compass(540, 760, 230, ts, fade(ts, 0.3, 1.5, 3.5, 5.0, 6.5))
             + _heartbeat(540, 760, 300, ts, fade(ts, 9.5, 11.0, 22, 32, 37))
             + _ring(540, 760, 300, ts, fade(ts, 7.5, 9.5, 24, 32, 38))
             + _attest(540, 760, ts, fade(ts, 14.5, 16.0, 21.0, 23.0, 24.5))
             + _umbra(540, 1180, 0.6, ts, fade(ts, 8.0, 10.0, 24, 31, 36)))
    deep = (f'<rect width="{W}" height="{H}" fill="url(#sky)"/>' + _clouds(ts, 0.95) + _cosmos(ts)
            + _quantum(ts, fade(ts, 1.5, 4.0, 30, 36, 40))
            + _datastream(ts, fade(ts, 2.0, 4.0, 30, 36, 40))
            + _neural(ts, fade(ts, 9.0, 12.0, 28, 33, 37)))
    screen = deep + f'<g transform="{_camera(ts)}">{world}</g>'
    hud = _hud(ts, fade(ts, 1.5, 3.5, 33, 36, 39))
    hud += _typed(f"> CHIMERA :: DAY {b['day']}", 90, 1000, ts, 0.6, ACID, 46, fade(ts, 0.5, 1.2, 4.6, 5.6, 6.8))
    hud += _panel(b["event"], V["a1"], fade(ts, 13.5, 14.5, 21, 22.5, 23.5))
    hud += _pulse_meter(ts, fade(ts, 9.0, 11.0, 3.0, 14.5, 16.0))  # day 18: PULSE senses operator -> fatigue -> gate
    hud += _ledger(ts, fade(ts, 15.5, 16.5, 8.0, 25.5, 26.8))
    hud += _panel(b.get("panel2", b["subtitle"]), AMBER, fade(ts, 24, 25, 30, 31.5, 32.5))
    tc = fade(ts, 32.5, 33.5, 36.5, 37, 38)
    hud += (f'<g opacity="{tc:.2f}" text-anchor="middle">'
            f'<text x="540" y="1380" font-family="{FONT}" font-size="64" fill="{WHITE}">DAY {b["day"]}</text>'
            f'<text x="540" y="1450" font-family="{FONT}" font-size="32" fill="{V["a1"]}">{esc(b["subtitle"])}</text>'
            f'<text x="540" y="1530" font-family="{FONT}" font-size="48" fill="{AMBER}">{b["modules_done"]} / 8</text>'
            f'<text x="540" y="1590" font-family="{FONT}" font-size="30" fill="{ACID}">{b["tests"]} TESTS GREEN</text></g>')
    hud += _qr_scene(ts, fade(ts, 38.5, 39.5, 44, 44.5, 45))
    overlay = f'<rect width="{W}" height="{H}" fill="url(#vign)"/>' + _sakura(ts, 0.85) + _glitch(ts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'{_defs()}{screen}{hud}{overlay}</svg>')
