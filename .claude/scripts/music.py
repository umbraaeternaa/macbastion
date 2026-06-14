#!/usr/bin/env python3
"""Multi-genre music synth (numpy/scipy, royalty-free, fully local) for the reel agent.

Every run is genuinely different — not a different drum style over the same riff. Axes:
  1. GENRE (17): two engines.
     * BAND/electronic grid: house, deep_house, techno, dnb, jungle, liquid, trance,
       psytrance, deep_progressive, electro, new_wave, pop, indie, indie_pop.
     * ACOUSTIC engines (their own structure, not a 4-on-the-floor grid):
       jazz (swing + walking bass + ii-V-I 7th comping), blues (12-bar shuffle + boogie
       bass + blue-scale lead), classical (broken-chord piano + string pad + melody, NO drums).
  2. MUSICAL CONTENT: a random KEY (12 roots) x SCALE (7 modes, major+minor families) x
     PROGRESSION x TEMPO per run, plus a generated MELODY line — so the actual notes,
     chords and mood change every time, not only the beat.

Timbres are built from vectorised additive / FM synthesis + ADSR, so it renders fast and
sounds warmer than raw saws (electric piano, bell, plucked string, string pad, piano,
organ, supersaw). HONEST framing (MANIFESTO §4): this is trend-INFORMED *procedural*
synthesis — beautiful and varied, generated on-device — not a sampled/streamed track.

Usage: music.py --dur 45 --out track.wav [--genre NAME] [--seed N]
Prints the chosen genre | key | bpm (so the reel log/caption can name it).
"""

from __future__ import annotations

import argparse

import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve

SR = 44100

# Band/electronic genres (grid engine) + acoustic engines (own structure).
BAND_GENRES = [
    "house", "deep_house", "techno", "dnb", "jungle", "liquid", "trance", "psytrance",
    "deep_progressive", "electro", "new_wave", "pop", "indie", "indie_pop",
]
ACOUSTIC_GENRES = ["jazz", "blues", "classical"]
GENRES = BAND_GENRES + ACOUSTIC_GENRES

# --- band profiles: BPM, drum grid (16th steps), voices, key bias, arrangement ---
# harmony: pad | stab | pluck | epiano | arp_chords    lead: None | arp | melody | squelch
# bass:    sub | rolling | reese | psy                 major: None(any) | True | False
PROFILES = {
    "house":            dict(bpm=124, bars=1, kick="house", k=[0,4,8,12], clap=[4,12], snare=[], hat="offbeat",
                             bass="sub", harmony="stab", lead=None, major=None, swing=0.0, wet=0.18),
    "deep_house":       dict(bpm=122, bars=1, kick="house", k=[0,4,8,12], clap=[4,12], snare=[], hat="shaker",
                             bass="sub", harmony="pad", lead=None, major=None, swing=0.04, wet=0.30),
    "techno":           dict(bpm=132, bars=1, kick="techno", k=[0,4,8,12], clap=[], snare=[], hat="16th",
                             bass="rolling", harmony="stab", lead=None, major=False, swing=0.0, wet=0.22),
    "dnb":              dict(bpm=174, bars=2, kick="dnb", k=[0,10,16,22], clap=[4,12,20,28], snare=[], hat="roll",
                             bass="reese", harmony="pad", lead=None, major=False, swing=0.10, wet=0.30),
    "jungle":           dict(bpm=166, bars=2, kick="dnb", k=[0,6,16,22], clap=[4,12,20,28], snare=[], hat="roll",
                             bass="sub", harmony="stab", lead=None, major=False, swing=0.16, wet=0.26),
    "liquid":           dict(bpm=172, bars=2, kick="dnb", k=[0,10,16,22], clap=[4,12,20,28], snare=[], hat="roll",
                             bass="reese", harmony="pad", lead="melody", major=None, swing=0.08, wet=0.34),
    "trance":           dict(bpm=138, bars=1, kick="house", k=[0,4,8,12], clap=[4,12], snare=[], hat="offbeat",
                             bass="rolling", harmony="pad", lead="arp", major=None, swing=0.0, wet=0.36),
    "psytrance":        dict(bpm=144, bars=1, kick="techno", k=[0,4,8,12], clap=[], snare=[], hat="offbeat",
                             bass="psy", harmony="pad", lead="squelch", major=False, swing=0.0, wet=0.30),
    # --- new (operator request, day 22): trend-informed musical genres ---
    "deep_progressive": dict(bpm=122, bars=1, kick="house", k=[0,4,8,12], clap=[4,12], snare=[], hat="shaker",
                             bass="rolling", harmony="pad", lead="arp", major=None, swing=0.0, wet=0.38),
    "electro":          dict(bpm=128, bars=1, kick="techno", k=[0,4,8,12], clap=[4,12], snare=[], hat="16th",
                             bass="rolling", harmony="stab", lead="squelch", major=None, swing=0.0, wet=0.22),
    "new_wave":         dict(bpm=120, bars=1, kick="house", k=[0,4,8,12], clap=[], snare=[4,12], hat="offbeat",
                             bass="rolling", harmony="arp_chords", lead="arp", major=True, swing=0.0, wet=0.30),
    "pop":              dict(bpm=116, bars=1, kick="house", k=[0,8], clap=[], snare=[4,12], hat="offbeat",
                             bass="sub", harmony="pluck", lead="melody", major=True, swing=0.0, wet=0.24),
    "indie":            dict(bpm=112, bars=1, kick="house", k=[0,8], clap=[], snare=[4,12], hat="shaker",
                             bass="sub", harmony="pluck", lead="melody", major=True, swing=0.06, wet=0.28),
    "indie_pop":        dict(bpm=120, bars=1, kick="house", k=[0,8], clap=[], snare=[4,12], hat="offbeat",
                             bass="sub", harmony="epiano", lead="melody", major=True, swing=0.0, wet=0.26),
}

# --- procedural harmony: a fresh key / scale / progression every run ---
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
SCALES = {
    "natural minor":  [0, 2, 3, 5, 7, 8, 10],
    "dorian":         [0, 2, 3, 5, 7, 9, 10],
    "phrygian":       [0, 1, 3, 5, 7, 8, 10],
    "harmonic minor": [0, 2, 3, 5, 7, 8, 11],
    "major":          [0, 2, 4, 5, 7, 9, 11],
    "mixolydian":     [0, 2, 4, 5, 7, 9, 10],
    "lydian":         [0, 2, 4, 6, 7, 9, 11],
}
MAJOR_SCALES = ("major", "mixolydian", "lydian")
# 4-chord progressions as 0-based scale degrees.
MIN_PROGS = [
    [0, 5, 3, 4], [0, 6, 5, 6], [0, 4, 5, 3], [0, 3, 4, 0],
    [0, 2, 5, 4], [0, 6, 3, 4], [0, 5, 6, 4],
]
MAJ_PROGS = [
    [0, 4, 5, 3], [0, 5, 3, 4], [5, 3, 0, 4], [0, 3, 4, 4],
    [0, 4, 3, 4], [3, 4, 0, 5], [0, 5, 4, 3],
]


def _m2f(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def _scale_midi(scale: list[int], deg: int) -> int:
    """Map a (possibly negative) scale degree to a semitone offset, octave-aware."""
    return 12 * (deg // 7) + scale[deg % 7]


def _make_harmony(rng, want_major=None):
    """Pick a random key + scale + progression. Returns (root_pc, name, scale, prog, is_major)."""
    if want_major is True:
        pool = list(MAJOR_SCALES)
    elif want_major is False:
        pool = ["natural minor", "dorian", "phrygian", "harmonic minor"]
    else:
        pool = list(SCALES)
    name = pool[int(rng.integers(len(pool)))]
    scale = SCALES[name]
    root_pc = int(rng.integers(12))
    is_major = name in MAJOR_SCALES
    prog = (MAJ_PROGS if is_major else MIN_PROGS)[int(rng.integers(7))]
    return root_pc, name, scale, prog, is_major


# --- envelopes -------------------------------------------------------------
def _env_perc(n, atk_s, dec):
    """Percussive: short linear attack (samples) then exponential decay (rate)."""
    t = np.arange(n) / SR
    e = np.exp(-t * dec)
    a = min(atk_s, n)
    if a > 1:
        e[:a] *= np.linspace(0, 1, a)
    return e.astype(np.float32)


def _env_pad(n, atk_s, rel_s):
    """Sustained: linear attack + linear release (both in samples)."""
    e = np.ones(n, dtype=np.float32)
    a, r = min(atk_s, n), min(rel_s, n)
    if a > 1:
        e[:a] = np.linspace(0, 1, a)
    if r > 1:
        e[-r:] *= np.linspace(1, 0, r)
    return e


# --- oscillators -----------------------------------------------------------
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


# --- voices (vectorised additive / FM timbres, peak ~1 before gain) --------
def _v_epiano(freq, n, rng=None):
    t = np.arange(n) / SR
    idx = 3.0 * np.exp(-t * 6)  # FM index decays -> bell-attack into a warm tone
    y = np.sin(2 * np.pi * freq * t + idx * np.sin(2 * np.pi * 2.0 * freq * t))
    return (y * _env_perc(n, int(0.004 * SR), 4.2)).astype(np.float32)


def _v_piano(freq, n, rng=None):
    t = np.arange(n) / SR
    parts, amps = (1, 2, 3, 4, 5, 6), (1.0, 0.5, 0.33, 0.2, 0.11, 0.06)
    y = sum(a * np.sin(2 * np.pi * freq * p * t) for p, a in zip(parts, amps)) / sum(amps)
    return (y * _env_perc(n, int(0.003 * SR), 4.6)).astype(np.float32)


def _v_pluck(freq, n, rng=None):
    t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * freq * t)
         + 0.4 * np.sin(2 * np.pi * 2 * freq * t)
         + 0.2 * np.sin(2 * np.pi * 3 * freq * t)) / 1.6
    return (y * _env_perc(n, int(0.002 * SR), 7.0)).astype(np.float32)


def _v_bell(freq, n, rng=None):
    t = np.arange(n) / SR
    idx = 4.0 * np.exp(-t * 3)
    y = np.sin(2 * np.pi * freq * t + idx * np.sin(2 * np.pi * 1.41 * freq * t))
    return (y * np.exp(-t * 2.2)).astype(np.float32)


def _v_strings(freq, n, rng=None):
    """Detuned-saw ensemble pad with a slow swell + gentle vibrato."""
    t = np.arange(n) / SR
    vib = 1.0 + 0.004 * np.sin(2 * np.pi * 5.2 * t)
    y = sum(_saw(freq * (1 + d) * vib[0], n) for d in (-0.012, 0, 0.012)) / 3.0
    return (y * _env_pad(n, int(0.18 * SR), int(0.28 * SR)) * 0.7).astype(np.float32)


def _v_organ(freq, n, rng=None):
    t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * freq * t)
         + 0.5 * np.sin(2 * np.pi * 2 * freq * t)
         + 0.3 * np.sin(2 * np.pi * 4 * freq * t)) / 1.8
    return (y * _env_pad(n, int(0.02 * SR), int(0.05 * SR))).astype(np.float32)


def _v_lead(freq, n, rng=None):
    """Bright supersaw lead with a little vibrato — sits on top of the mix."""
    t = np.arange(n) / SR
    y = _supersaw(freq, n, 0.02)
    y *= 1.0 + 0.02 * np.sin(2 * np.pi * 5.5 * t)
    return (y * _env_perc(n, int(0.01 * SR), 4.5)).astype(np.float32)


def _v_bass_note(freq, n, rng=None):
    """Plucked acoustic-ish bass for walking/boogie lines."""
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * freq * t) + 0.25 * _saw(freq, n)
    return (y * _env_perc(n, int(0.004 * SR), 3.2)).astype(np.float32)


VOICES = {
    "epiano": _v_epiano, "piano": _v_piano, "pluck": _v_pluck, "bell": _v_bell,
    "strings": _v_strings, "organ": _v_organ, "lead": _v_lead,
}


# --- drums -----------------------------------------------------------------
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


def _snare(rng):
    n = int(0.18 * SR); t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t * 30)
    noise = rng.standard_normal(n) * np.exp(-t * 24)
    return (0.5 * tone + 0.85 * noise).astype(np.float32) * 0.7


def _brush(rng):
    """Soft brushed-snare swish for jazz."""
    n = int(0.20 * SR); t = np.arange(n) / SR
    return (rng.standard_normal(n) * np.exp(-t * 11)).astype(np.float32) * 0.5


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


def _finalize(mix, rng, wet, drive=1.2):
    mix = _reverb(mix, rng, wet)
    mix = np.tanh(mix * drive)
    mix /= np.max(np.abs(mix)) + 1e-9
    mix *= 0.94
    fi, fo = int(0.4 * SR), int(1.2 * SR)
    mix[:fi] *= np.linspace(0, 1, fi); mix[-fo:] *= np.linspace(1, 0, fo)
    return mix.astype(np.float32)


# --- shared melody generator ----------------------------------------------
def _melody_line(rng, scale, root_midi, prog, dur, beat, block, voice,
                 dens=0.6, gain=0.2, oct_off=24, swing=0.0):
    """A musical lead over the progression: random-walk within the scale, biased to
    chord tones on strong eighths, with rests. Returns a mono buffer."""
    n = int(dur * SR); out = np.zeros(n, dtype=np.float32)
    eighth = beat / 2.0
    ne = int(dur / eighth)
    deg = 0
    for e in range(ne):
        t = e * eighth + (swing * beat if e % 2 else 0.0)
        strong = (e % 2 == 0)
        if not strong and rng.random() > dens:
            continue
        chord_deg = prog[int((e * eighth) // block) % len(prog)]
        if strong and rng.random() < 0.6:
            deg = chord_deg + (0, 2, 4)[int(rng.integers(3))]
        else:
            deg = max(-3, min(11, deg + int(rng.integers(-2, 3))))
        midi = root_midi + oct_off + _scale_midi(scale, deg)
        length = eighth * (2 if rng.random() < 0.4 else 1)
        nn = max(1, int(length * 0.95 * SR))
        _place(out, voice(_m2f(midi), nn, rng), t, gain)
    return out


# --- BAND / electronic grid engine -----------------------------------------
def synth_band(genre, dur, seed):
    rng = np.random.default_rng(seed)
    p = PROFILES[genre]
    bpm = max(90, p["bpm"] + int(rng.integers(-4, 5)))
    root_pc, sname, scale, prog, is_major = _make_harmony(rng, p.get("major"))
    beat = 60.0 / bpm; bar = 4 * beat; step = bar / 16.0
    block = p["bars"] * bar
    n = int(dur * SR); nb = int(np.ceil(dur / block))
    bass_base = 33 + root_pc

    roots, chords, chord_midis = [], [], []
    for deg in prog:
        bm = bass_base + _scale_midi(scale, deg)
        while bm > 47:
            bm -= 12
        roots.append(_m2f(bm))
        cm = [bass_base + 12 + _scale_midi(scale, deg + k) for k in (0, 2, 4)]
        chord_midis.append(cm)
        chords.append([_m2f(x) for x in cm])

    # drums
    drums = np.zeros(n, dtype=np.float32)
    kick, clap, snare = _kick(rng, p["kick"]), _clap(rng), _snare(rng)
    for b in range(nb):
        t0 = b * block
        for s in p["k"]:
            _place(drums, kick, t0 + s * step, 1.0)
        for s in p["clap"]:
            _place(drums, clap, t0 + s * step, 0.8)
        for s in p.get("snare", []):
            _place(drums, snare, t0 + s * step, 0.8)
        for s in range(16 * p["bars"]):
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
        f = roots[b % len(roots)]
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
    hkind = p["harmony"]
    for b in range(nb):
        i0, i1 = int(b * block * SR), min(n, int((b + 1) * block * SR))
        m = i1 - i0
        if m <= 0:
            break
        seg = np.arange(m) / SR
        chord = chords[b % len(chords)]
        cmid = chord_midis[b % len(chord_midis)]
        if hkind == "pad":
            v = sum(np.sin(2 * np.pi * c * seg) + 0.35 * _saw(c, m) for c in chord) / len(chord)
            env = np.clip(np.minimum(seg / 0.4, (block - seg) / 0.6), 0, 1)
            harm[i0:i1] += (v * 0.20 * env).astype(np.float32)
        elif hkind == "stab":
            for s in range(0, 16 * p["bars"], 4):
                sl = int(0.18 * SR); tt = np.arange(sl) / SR
                v = sum(np.sin(2 * np.pi * c * tt) for c in chord) / len(chord)
                _place(harm, (v * np.exp(-tt * 9)).astype(np.float32), b * block + s * step, 0.5)
        elif hkind in ("pluck", "epiano"):  # comp the chord on each beat
            voice = VOICES["pluck" if hkind == "pluck" else "epiano"]
            for q in range(4 * p["bars"]):
                for mm in (cmid[0], cmid[1], cmid[2], cmid[0] + 12):
                    _place(harm, voice(_m2f(mm), int(beat * 1.1 * SR), rng), b * block + q * beat, 0.16)
        elif hkind == "arp_chords":  # arpeggiate chord tones across the bar (8ths)
            seq = [cmid[0], cmid[1], cmid[2], cmid[0] + 12]
            for s8 in range(8 * p["bars"]):
                mm = seq[s8 % len(seq)]
                _place(harm, VOICES["pluck"](_m2f(mm), int(beat * 0.6 * SR), rng),
                        b * block + s8 * (beat / 2.0), 0.18)

    # lead
    lead = np.zeros(n, dtype=np.float32)
    lkind = p["lead"]
    if lkind == "melody":
        lead = _melody_line(rng, scale, bass_base, prog, dur, beat, block,
                            VOICES["lead"] if is_major is None else VOICES["epiano"],
                            dens=0.62, gain=0.20, oct_off=24, swing=p["swing"])
    elif lkind in ("arp", "squelch"):
        for s in range(int(dur / step)):
            note = chords[(s // 4) % len(chords)][s % 3] * 2
            sl = int(step * SR); tt = np.arange(sl) / SR
            if lkind == "arp":
                v = _supersaw(note, sl, 0.02) * np.exp(-tt * 6)
            else:
                v = _lpf(_saw(note, sl), 300 + 2500 * np.abs(np.sin(2 * np.pi * 0.5 * (s * step)))) * np.exp(-tt * 4)
            _place(lead, (v * 0.18).astype(np.float32), s * step, 1.0)

    mix = drums * 0.9 + bass * 0.85 + harm + lead
    return _finalize(mix, rng, p["wet"]), f"{genre} | {NOTE_NAMES[root_pc]} {sname} | {bpm}bpm"


# --- JAZZ engine: swing, walking bass, ii-V-I 7th comping, brushed kit ------
def synth_jazz(dur, seed):
    rng = np.random.default_rng(seed)
    bpm = 116 + int(rng.integers(-10, 12)); beat = 60.0 / bpm; bar = 4 * beat
    n = int(dur * SR); nb = int(np.ceil(dur / bar))
    root_pc = int(rng.integers(12))
    sname = "dorian" if rng.random() < 0.5 else "major"
    scale = SCALES[sname]
    prog = [1, 4, 0, 0] if rng.random() < 0.5 else [1, 4, 0, 5]  # ii-V-I-(I|vi)
    bass_base = 31 + root_pc  # walking-bass register
    swing = 0.12

    drums = np.zeros(n, dtype=np.float32)
    bass = np.zeros(n, dtype=np.float32)
    harm = np.zeros(n, dtype=np.float32)
    for b in range(nb):
        cd, ncd = prog[b % len(prog)], prog[(b + 1) % len(prog)]
        # walking bass: chord tones on beats 1-3, chromatic approach to next root on 4
        root = bass_base + _scale_midi(scale, cd)
        nroot = bass_base + _scale_midi(scale, ncd)
        tones = [root, root + (scale[(cd + 2) % 7] - scale[cd % 7]) % 12,
                 root + 7, root + (scale[(cd + 5) % 7] - scale[cd % 7]) % 12]
        for q in range(4):
            mm = tones[q] if q < 3 else (nroot - 1 if nroot >= root else nroot + 1)
            _place(bass, _v_bass_note(_m2f(mm), int(beat * 0.95 * SR), rng), b * bar + q * beat, 0.8)
        # comp a 7th chord on the off-beats of 2 and 4 (epiano)
        chord = [bass_base + 12 + _scale_midi(scale, cd + k) for k in (0, 2, 4, 6)]
        for off in (1.5 * beat, 3.5 * beat):
            for mm in chord:
                _place(harm, _v_epiano(_m2f(mm), int(beat * 1.3 * SR), rng), b * bar + off, 0.14)
        # ride (swung 8ths) + brushed snare on 2 & 4 + feathered kick on 1 & 3
        for q in range(4):
            _place(drums, _hat(rng, 0.05), b * bar + q * beat, 0.32)
            _place(drums, _hat(rng, 0.05), b * bar + q * beat + (1 - swing) * beat, 0.22)
        _place(drums, _brush(rng), b * bar + 1 * beat, 0.6)
        _place(drums, _brush(rng), b * bar + 3 * beat, 0.6)
        _place(drums, _kick(rng, "house"), b * bar + 0 * beat, 0.35)
        _place(drums, _kick(rng, "house"), b * bar + 2 * beat, 0.30)

    lead = _melody_line(rng, scale, bass_base, prog, dur, beat, bar,
                        _v_epiano, dens=0.5, gain=0.18, oct_off=24, swing=swing)
    mix = drums * 0.7 + bass * 0.9 + harm + lead
    return _finalize(mix, rng, 0.30), f"jazz | {NOTE_NAMES[root_pc]} {sname} | {bpm}bpm swing"


# --- BLUES engine: 12-bar shuffle, boogie bass, blue-scale lead -------------
def synth_blues(dur, seed):
    rng = np.random.default_rng(seed)
    bpm = 92 + int(rng.integers(-8, 12)); beat = 60.0 / bpm; bar = 4 * beat
    n = int(dur * SR); nb = int(np.ceil(dur / bar))
    root_pc = int(rng.integers(12))
    base = 33 + root_pc
    # 12-bar blues in scale-degree roots (I-IV-V as 0/3/4 of a major-ish scale)
    bars12 = [0, 0, 0, 0, 3, 3, 0, 0, 4, 3, 0, 4]
    maj = SCALES["mixolydian"]
    blue = [0, 3, 5, 6, 7, 10]  # blues scale for the lead
    boogie = [0, 4, 7, 9, 10, 9, 7, 4]  # classic shuffle boogie (semitone offsets)
    shuf = beat * (2.0 / 3.0)  # triplet shuffle: hits on 1 and the 3rd triplet

    drums = np.zeros(n, dtype=np.float32)
    bass = np.zeros(n, dtype=np.float32)
    for b in range(nb):
        root = base + _scale_midi(maj, bars12[b % 12])
        for e in range(8):  # boogie bass over 8 eighths
            _place(bass, _v_bass_note(_m2f(root + boogie[e]), int(beat * 0.46 * SR), rng),
                    b * bar + e * (beat / 2.0), 0.8)
        for q in range(4):  # shuffle hat + backbeat snare + kick on 1 & 3
            _place(drums, _hat(rng, 0.045), b * bar + q * beat, 0.30)
            _place(drums, _hat(rng, 0.045), b * bar + q * beat + shuf, 0.22)
        _place(drums, _snare(rng), b * bar + 1 * beat, 0.6)
        _place(drums, _snare(rng), b * bar + 3 * beat, 0.6)
        _place(drums, _kick(rng, "house"), b * bar + 0 * beat, 0.8)
        _place(drums, _kick(rng, "house"), b * bar + 2 * beat, 0.7)

    # blue-scale lead with a shuffle phrasing
    lead = np.zeros(n, dtype=np.float32)
    ne = int(dur / (beat / 2.0)); cur = 0
    for e in range(ne):
        if e % 2 and rng.random() > 0.55:
            continue
        t = e * (beat / 2.0) + (shuf - beat / 2.0 if e % 2 else 0.0)
        b = int(t // bar)
        root = base + _scale_midi(maj, bars12[b % 12])
        cur = max(0, min(len(blue) - 1, cur + int(rng.integers(-2, 3))))
        midi = root + 12 + blue[cur] + 12 * int(rng.random() < 0.3)
        _place(lead, _v_lead(_m2f(midi), int((beat / 2.0) * 0.9 * SR), rng), t, 0.18)
    mix = drums * 0.8 + bass * 0.9 + lead
    return _finalize(mix, rng, 0.24), f"blues | {NOTE_NAMES[root_pc]} 12-bar | {bpm}bpm shuffle"


# --- CLASSICAL engine: broken-chord piano + string pad + melody, NO drums ---
def synth_classical(dur, seed):
    rng = np.random.default_rng(seed)
    bpm = 72 + int(rng.integers(-8, 14)); beat = 60.0 / bpm; bar = 4 * beat
    n = int(dur * SR); nb = int(np.ceil(dur / bar))
    root_pc, sname, scale, prog, is_major = _make_harmony(rng)
    # a longer 8-chord journey for the arc
    prog = prog + [(prog[i] + 2) % 7 for i in range(4)]
    base = 36 + root_pc

    piano = np.zeros(n, dtype=np.float32)
    pad = np.zeros(n, dtype=np.float32)
    for b in range(nb):
        cd = prog[b % len(prog)]
        cmid = [base + _scale_midi(scale, cd + k) for k in (0, 2, 4)]
        # Alberti-style broken chord across 8 eighths: low-high-mid-high
        seq = [cmid[0], cmid[2] + 12, cmid[1], cmid[2] + 12]
        for e in range(8):
            _place(piano, _v_piano(_m2f(seq[e % 4]), int(beat * 0.6 * SR), rng),
                    b * bar + e * (beat / 2.0), 0.34)
        # sustained string pad on the chord (an octave up)
        i0 = int(b * bar * SR); m = min(n, int((b + 1) * bar * SR)) - i0
        if m > 0:
            for mm in cmid:
                seg = _v_strings(_m2f(mm + 12), m, rng)
                pad[i0:i0 + m] += seg[:m] * 0.16

    melody = _melody_line(rng, scale, base, prog, dur, beat, bar,
                          _v_strings, dens=0.5, gain=0.16, oct_off=24)
    mix = piano + pad + melody
    return _finalize(mix, rng, 0.42, drive=1.05), f"classical | {NOTE_NAMES[root_pc]} {sname} | {bpm}bpm"


def synth(genre: str, dur: float, seed: int | None) -> tuple[np.ndarray, str]:
    if genre == "jazz":
        return synth_jazz(dur, seed)
    if genre == "blues":
        return synth_blues(dur, seed)
    if genre == "classical":
        return synth_classical(dur, seed)
    return synth_band(genre, dur, seed)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dur", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--genre", default=None)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    genre = a.genre if a.genre in GENRES else GENRES[int(rng.integers(len(GENRES)))]
    audio, info = synth(genre, a.dur, a.seed)
    wavfile.write(a.out, SR, audio)
    print(f"OK music: {a.out}  {info}  peak {np.max(np.abs(audio)):.2f}")


if __name__ == "__main__":
    main()
