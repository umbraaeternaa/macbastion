#!/usr/bin/env python3
"""Multi-genre electronic music synth (numpy, royalty-free) for the reel agent.

Picks a RANDOM genre + random seed every run, so each day's track is new and in a
(possibly) different style. Genres: house, deep_house, techno, dnb, jungle, liquid,
trance, psytrance. Each is a PROFILE of parameters fed to one shared engine — distinct
BPM, drum pattern, bass voice, harmony and lead, so they sound genuinely different.

Usage: music.py --dur 45 --out track.wav [--genre NAME] [--seed N]
Prints the chosen genre (so the reel log/caption can name it).
"""

from __future__ import annotations

import argparse

import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve

SR = 44100
GENRES = ["house", "deep_house", "techno", "dnb", "jungle", "liquid", "trance", "psytrance"]

# --- profiles: BPM, drum grid (16th steps over 1 or 2 bars), voices ---
PROFILES = {
    "house":      dict(bpm=124, bars=1, kick="house", k=[0,4,8,12], clap=[4,12], hat="offbeat",
                       bass="sub", harmony="stab", lead=None, swing=0.0, wet=0.18),
    "deep_house": dict(bpm=122, bars=1, kick="house", k=[0,4,8,12], clap=[4,12], hat="shaker",
                       bass="sub", harmony="pad", lead=None, swing=0.04, wet=0.30),
    "techno":     dict(bpm=132, bars=1, kick="techno", k=[0,4,8,12], clap=[], hat="16th",
                       bass="rolling", harmony="stab", lead=None, swing=0.0, wet=0.22),
    "dnb":        dict(bpm=174, bars=2, kick="dnb", k=[0,10,16,22], clap=[4,12,20,28], hat="roll",
                       bass="reese", harmony="pad", lead=None, swing=0.10, wet=0.30),
    "jungle":     dict(bpm=166, bars=2, kick="dnb", k=[0,6,16,22], clap=[4,12,20,28], hat="roll",
                       bass="sub", harmony="stab", lead=None, swing=0.16, wet=0.26),
    "liquid":     dict(bpm=172, bars=2, kick="dnb", k=[0,10,16,22], clap=[4,12,20,28], hat="roll",
                       bass="reese", harmony="pad", lead=None, swing=0.08, wet=0.34),
    "trance":     dict(bpm=138, bars=1, kick="house", k=[0,4,8,12], clap=[4,12], hat="offbeat",
                       bass="rolling", harmony="pad", lead="arp", swing=0.0, wet=0.36),
    "psytrance":  dict(bpm=144, bars=1, kick="techno", k=[0,4,8,12], clap=[], hat="offbeat",
                       bass="psy", harmony="pad", lead="squelch", swing=0.0, wet=0.30),
}

# D-minor-ish material reused across genres (Hz). Roots per bar and chord stacks.
ROOTS = [73.42, 58.27, 87.31, 65.41]  # D2 Bb1 F2 C2
CHORDS = [[146.83,174.61,220.0],[116.54,146.83,174.61],[130.81,174.61,220.0],[130.81,164.81,196.0]]


def _saw(freq, n):
    t = np.arange(n) / SR
    return 2.0 * ((t * freq) % 1.0) - 1.0


def _supersaw(freq, n, det=0.02):
    return sum(_saw(freq * (1 + d), n) for d in (-det, 0, det)) / 3.0


def _lpf(x, cutoff):
    a = np.exp(-2 * np.pi * np.asarray(cutoff) / SR)
    a = np.broadcast_to(a, x.shape)
    y = np.empty_like(x); prev = 0.0
    for i in range(len(x)):
        prev = (1 - a[i]) * x[i] + a[i] * prev
        y[i] = prev
    return y


def _kick(rng, style):
    n = int(0.22 * SR); t = np.arange(n) / SR
    if style == "house":
        f = 50 + (130 - 50) * np.exp(-t * 55); dec = 20
    elif style == "techno":
        f = 45 + (115 - 45) * np.exp(-t * 42); dec = 11
    else:
        f = 45 + (95 - 45) * np.exp(-t * 38); dec = 16
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * dec)
    return (body + rng.standard_normal(n) * np.exp(-t * 260) * 0.22).astype(np.float32)


def _clap(rng):
    n = int(0.16 * SR); t = np.arange(n) / SR
    return (rng.standard_normal(n) * np.exp(-t * 28)).astype(np.float32) * 0.7


def _hat(rng, dur=0.04, op=False):
    n = int(dur * SR); t = np.arange(n) / SR
    return (np.diff(rng.standard_normal(n + 1)) * np.exp(-t * (26 if op else 95)) * 0.4).astype(np.float32)


def _place(buf, s, at, g=1.0):
    i = int(at * SR); j = min(len(buf), i + len(s))
    if i < len(buf):
        buf[i:j] += s[: j - i] * g


def _reverb(x, rng, wet):
    ir_n = int(0.9 * SR)
    ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / (0.25 * SR))
    w = fftconvolve(x, ir)[: len(x)]; w /= np.max(np.abs(w)) + 1e-9
    return (1 - wet) * x + wet * w


def synth(genre: str, dur: float, seed: int | None) -> np.ndarray:
    rng = np.random.default_rng(seed)
    p = PROFILES[genre]
    beat = 60.0 / p["bpm"]; bar = 4 * beat; step = bar / 16.0
    block = p["bars"] * bar
    n = int(dur * SR)
    nb = int(np.ceil(dur / block))

    drums = np.zeros(n, dtype=np.float32)
    kick, clap = _kick(rng, p["kick"]), _clap(rng)
    for b in range(nb):
        t0 = b * block
        steps16 = 16 * p["bars"]
        for s in p["k"]:
            _place(drums, kick, t0 + s * step, 1.0)
        for s in p["clap"]:
            _place(drums, clap, t0 + s * step, 0.8)
        for s in range(steps16):
            sw = step * p["swing"] if s % 2 else 0.0
            if p["hat"] == "offbeat" and s % 4 == 2:
                _place(drums, _hat(rng, 0.08, op=True), t0 + s * step + sw, 0.5)
            elif p["hat"] == "16th":
                _place(drums, _hat(rng), t0 + s * step + sw, 0.35)
            elif p["hat"] == "shaker" and s % 2:
                _place(drums, _hat(rng, 0.05), t0 + s * step + sw, 0.3)
            elif p["hat"] == "roll":
                _place(drums, _hat(rng), t0 + s * step + sw, 0.42)

    # bass
    bass = np.zeros(n, dtype=np.float32)
    for b in range(nb):
        i0, i1 = int(b * block * SR), min(n, int((b + 1) * block * SR))
        m = i1 - i0
        if m <= 0:
            break
        seg = np.arange(m) / SR
        f = ROOTS[b % len(ROOTS)]
        if p["bass"] == "reese":
            layers = _supersaw(f, m, 0.015)
            lfo = 600 + 500 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.35 * seg))
            voiced = _lpf(layers, lfo)
            bass[i0:i1] += (voiced * 0.7 + np.sin(2 * np.pi * (f / 2) * seg) * 0.5).astype(np.float32)
        elif p["bass"] in ("rolling", "psy"):
            env = ((np.arange(m) / (step * SR)) % 1.0)
            gate = (env > 0.5).astype(float) if p["bass"] == "rolling" else (env > 0.35).astype(float)
            tone = _saw(f, m) if p["bass"] == "psy" else np.sin(2 * np.pi * f * seg)
            cut = 400 if p["bass"] == "psy" else 250
            bass[i0:i1] += (_lpf(tone * gate, cut) * 0.8).astype(np.float32)
        else:  # sub
            bass[i0:i1] += (np.sin(2 * np.pi * f * seg) * 0.8).astype(np.float32)

    # harmony
    harm = np.zeros(n, dtype=np.float32)
    for b in range(nb):
        i0, i1 = int(b * block * SR), min(n, int((b + 1) * block * SR))
        m = i1 - i0
        if m <= 0:
            break
        seg = np.arange(m) / SR
        chord = CHORDS[b % len(CHORDS)]
        if p["harmony"] == "pad":
            v = sum(np.sin(2 * np.pi * c * seg) + 0.35 * _saw(c, m) for c in chord) / len(chord)
            env = np.clip(np.minimum(seg / 0.4, (block - seg) / 0.6), 0, 1)
            harm[i0:i1] += (v * 0.20 * env).astype(np.float32)
        elif p["harmony"] == "stab":
            for s in range(0, 16 * p["bars"], 4):
                st = s * step
                sl = int(0.18 * SR); tt = np.arange(sl) / SR
                v = sum(np.sin(2 * np.pi * c * tt) for c in chord) / len(chord)
                _place(harm, (v * np.exp(-tt * 9)).astype(np.float32), b * block + st, 0.5)

    # lead
    lead = np.zeros(n, dtype=np.float32)
    if p["lead"] in ("arp", "squelch"):
        seg_all = np.arange(n) / SR
        for s in range(int(dur / step)):
            note = CHORDS[(s // 4) % len(CHORDS)][s % 3] * 2
            sl = int(step * SR); tt = np.arange(sl) / SR
            if p["lead"] == "arp":
                v = _supersaw(note, sl, 0.02) * np.exp(-tt * 6)
            else:
                v = _lpf(_saw(note, sl), 300 + 2500 * np.abs(np.sin(2 * np.pi * 0.5 * (s * step)))) * np.exp(-tt * 4)
            _place(lead, (v * 0.18).astype(np.float32), s * step, 1.0)

    mix = drums * 0.9 + bass * 0.85 + harm + lead
    mix = _reverb(mix, rng, p["wet"])
    mix = np.tanh(mix * 1.2)
    mix /= np.max(np.abs(mix)) + 1e-9
    mix *= 0.94
    fi, fo = int(0.4 * SR), int(1.2 * SR)
    mix[:fi] *= np.linspace(0, 1, fi); mix[-fo:] *= np.linspace(1, 0, fo)
    return mix.astype(np.float32)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dur", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--genre", default=None)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    genre = a.genre if a.genre in PROFILES else GENRES[int(rng.integers(len(GENRES)))]
    audio = synth(genre, a.dur, a.seed)
    wavfile.write(a.out, SR, audio)
    print(f"OK music: {a.out}  genre={genre}  {a.dur:.1f}s  peak {np.max(np.abs(audio)):.2f}")


if __name__ == "__main__":
    main()
