#!/usr/bin/env python3
"""Liquid DnB / jungle track synth — numpy, royalty-free (reel spec §11 / §14.5).

174 BPM, D-minor. Reconstructed from the production handoff: 2-bar break
(KICK[0,10,16,22] SNARE[4,12,20,28] GHOST[7,14,19,30]) + swung 16th hats, a Reese
bass (3 detuned saws -> 1-pole LPF with a slow LFO + sub-octave), lush pads
Dm->Bb->F->C (2 bars each), a low drone, an intro reverse-swell, convolution reverb
(decaying-noise IR ~0.9s, wet ~0.30), tanh soft-limit, normalise to 0.94, fade in/out.

A NEW track every run (random seed unless --seed is given) — the operator wants a
fresh track per reel.

Usage: music_dnb.py --dur 45 --out track.wav [--seed N]
"""

from __future__ import annotations

import argparse

import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve

SR = 44100
BPM = 174.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
STEP = BAR / 16.0  # 16th-note grid

# Reese note per 2 bars (Hz): D2, Bb1, F2, C2
BASS_NOTES = [73.42, 58.27, 87.31, 65.41]
# Pad chords (root sets, Hz) Dm -> Bb -> F -> C
PAD_CHORDS = [
    [146.83, 174.61, 220.00],  # Dm  (D4 F4 A4)
    [116.54, 146.83, 174.61],  # Bb  (Bb F D)
    [130.81, 174.61, 220.00],  # F   (F A C-ish)
    [130.81, 164.81, 196.00],  # C   (C E G)
]
DRONE = [36.71, 73.42]  # D1 + D2


def _saw(freq: np.ndarray | float, n: int) -> np.ndarray:
    t = np.arange(n) / SR
    ph = (t * freq) % 1.0 if np.isscalar(freq) else (np.cumsum(freq) / SR) % 1.0
    return 2.0 * ph - 1.0


def _one_pole_lpf(x: np.ndarray, cutoff_hz: np.ndarray | float) -> np.ndarray:
    # time-varying 1-pole low-pass; cutoff may be an array (LFO sweep)
    a = np.exp(-2 * np.pi * np.asarray(cutoff_hz) / SR)
    a = np.broadcast_to(a, x.shape)
    y = np.empty_like(x)
    prev = 0.0
    for i in range(len(x)):
        prev = (1 - a[i]) * x[i] + a[i] * prev
        y[i] = prev
    return y


def _kick(rng: np.random.Generator) -> np.ndarray:
    n = int(0.20 * SR)
    t = np.arange(n) / SR
    f = 45 + (95 - 45) * np.exp(-t * 38)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16)
    click = rng.standard_normal(n) * np.exp(-t * 260) * 0.30
    return (body + click).astype(np.float32)


def _snare(rng: np.random.Generator) -> np.ndarray:
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t * 26) * 0.5
    noise = rng.standard_normal(n) * np.exp(-t * 22)
    return (tone + noise * 0.8).astype(np.float32)


def _hat(rng: np.random.Generator, dur: float = 0.05) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = np.diff(rng.standard_normal(n + 1))  # crude hi-pass
    return (noise * np.exp(-t * 90) * 0.4).astype(np.float32)


def _place(buf: np.ndarray, sample: np.ndarray, at: float, gain: float = 1.0) -> None:
    i = int(at * SR)
    j = min(len(buf), i + len(sample))
    if i < len(buf):
        buf[i:j] += sample[: j - i] * gain


def _reverb(x: np.ndarray, rng: np.random.Generator, wet: float = 0.30) -> np.ndarray:
    ir_n = int(0.9 * SR)
    ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / (0.25 * SR))
    wetsig = fftconvolve(x, ir)[: len(x)]
    wetsig /= np.max(np.abs(wetsig)) + 1e-9
    return (1 - wet) * x + wet * wetsig


def synth(dur: float, seed: int | None) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    drums = np.zeros(n, dtype=np.float32)
    kick, snare = _kick(rng), _snare(rng)

    two_bar = 2 * BAR
    n_blocks = int(np.ceil(dur / two_bar))
    KICK, SNARE, GHOST = [0, 10, 16, 22], [4, 12, 20, 28], [7, 14, 19, 30]
    for b in range(n_blocks):
        t0 = b * two_bar
        for s in KICK:
            _place(drums, kick, t0 + s * STEP, 1.0)
        for s in SNARE:
            _place(drums, snare, t0 + s * STEP, 0.9)
        for s in GHOST:
            _place(drums, snare, t0 + s * STEP, 0.32)
        for s in range(32):  # swung 16th hats over the 2-bar block
            sw = STEP * 0.18 if s % 2 else 0.0
            _place(drums, _hat(rng), t0 + s * STEP + sw, 0.5)

    # Reese bass — one note per 2 bars, LFO-swept LPF + sub octave
    bass = np.zeros(n, dtype=np.float32)
    for b in range(n_blocks):
        i0 = int(b * two_bar * SR)
        i1 = min(n, int((b + 1) * two_bar * SR))
        m = i1 - i0
        if m <= 0:
            break
        f = BASS_NOTES[b % len(BASS_NOTES)]
        seg = np.arange(m) / SR
        layers = (
            _saw(f * (2 ** (-0.18 / 12)), m)
            + _saw(f, m)
            + _saw(f * (2 ** (0.22 / 12)), m)
        ) / 3.0
        lfo = 600 + 500 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.35 * seg))
        voiced = _one_pole_lpf(layers, lfo)
        sub = np.sin(2 * np.pi * (f / 2) * seg) * 0.5
        bass[i0:i1] += (voiced * 0.8 + sub).astype(np.float32)

    # Pads — sine+octave+soft saw, 2 bars each
    pads = np.zeros(n, dtype=np.float32)
    for b in range(n_blocks):
        i0 = int(b * two_bar * SR)
        i1 = min(n, int((b + 1) * two_bar * SR))
        m = i1 - i0
        if m <= 0:
            break
        seg = np.arange(m) / SR
        chord = PAD_CHORDS[b % len(PAD_CHORDS)]
        voice = np.zeros(m)
        for f in chord:
            voice += np.sin(2 * np.pi * f * seg) + 0.4 * _saw(f, m)
        env = np.minimum(1.0, seg / 0.4) * np.minimum(1.0, (two_bar - seg) / 0.6)
        pads[i0:i1] += (voice / len(chord) * 0.22 * np.clip(env, 0, 1)).astype(np.float32)

    # Drone
    seg = np.arange(n) / SR
    drone = sum(np.sin(2 * np.pi * f * seg) for f in DRONE) * 0.10

    # Intro reverse-swell 0..2s
    swell_n = int(2.0 * SR)
    swell = np.zeros(n)
    ramp = (np.linspace(0, 1, swell_n) ** 2)
    swell[:swell_n] = rng.standard_normal(swell_n) * ramp * 0.25

    mix = drums * 0.9 + bass * 0.85 + pads + drone + swell
    mix = _reverb(mix, rng, wet=0.30)
    mix = np.tanh(mix * 1.25)
    mix /= np.max(np.abs(mix)) + 1e-9
    mix *= 0.94

    # fade in 0.4 / out 1.2
    fi, fo = int(0.4 * SR), int(1.2 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)
    mix[-fo:] *= np.linspace(1, 0, fo)
    return mix.astype(np.float32)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dur", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    audio = synth(a.dur, a.seed)
    wavfile.write(a.out, SR, audio)
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(audio**2)))
    print(f"OK music: {a.out}  ({a.dur:.1f}s, 174 BPM Dm, peak {peak:.2f}, rms {rms:.2f})")


if __name__ == "__main__":
    main()
