"""PULSE scoring engine (§5.5, slice 1) — pure, hermetic.

Maps already-aggregated cognitive-load signals to a fatigue_score in [0,1] and a
friction mode (§3, §4). It takes pre-computed/normalized signals plus a baseline
snapshot as input; it NEVER reads MIRROR/ORACLE/SQLite/hardware (those feed it from
later slices). Deterministic, isolated, no IPC.

⚠️ Fail-safe direction (the OPPOSITE of VAULT): on a missing or broken signal PULSE
degrades toward LESS friction (mode 'normal'), NEVER toward block. A broken sensor
must not lock the operator out — the autonomy invariant (§8). PULSE is advisory: it
returns (score, mode); core is the only component that enforces a gate (§5).

Spec disambiguation made explicit here (not silently): mode boundaries are half-open
[lo, hi) with 1.0 -> exhausted (PE-6); delta = clamp(Δ/baseline, 0, 1) in the fatigue
direction (PE-1/PE-3). These pin §3/§4 ambiguities; if the spec intended otherwise,
raise it separately.

slice 1 is RED — the logic is not implemented yet (raises NotImplementedError). The
public surface (types + function signatures) is fixed so the failing tests are real.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Friction modes (§4). The effect on danger actions is enforced by core, not here.
MODE_NORMAL = "normal"
MODE_CAUTION = "caution"
MODE_TIRED = "tired"
MODE_EXHAUSTED = "exhausted"


@dataclass(frozen=True)
class Weights:
    """Signal-group weights (§3). Must sum to 1.0 (validated in score_and_mode, not
    at construction, so degraded renormalization can rescale a subset)."""

    w_a: float = 0.55  # group A — input patterns (MIRROR aggregates)
    w_b: float = 0.30  # group B — temporal context (clock/idle/session)
    w_c: float = 0.15  # group C — behavioral drift (ORACLE anomaly)


@dataclass(frozen=True)
class Signals:
    """Already-normalized signal values in [0,1]. A None field means that group is
    absent for this tick (MIRROR off -> input_delta None; ORACLE off -> drift None).
    Present groups' weights renormalize to sum 1.0 (§7)."""

    input_delta: float | None = None
    temporal: float | None = None
    drift: float | None = None


# Module-level singleton for the default-weights argument (frozen -> safe to share;
# avoids a call in the function default, ruff B008).
_DEFAULT_WEIGHTS = Weights()


def normalize_delta(current: float, baseline: float, higher_is_fatigue: bool) -> float:
    """Normalize a raw signal against its 14-day baseline into a [0,1] fatigue delta,
    measured in the fatigue direction. higher_is_fatigue=True: above baseline is
    fatigue (e.g. delete rate); False: below baseline is fatigue (e.g. typing speed).
    Returns clamp(Δ/baseline, 0, 1); the non-fatigue direction yields 0 (never < 0)."""
    if baseline == 0 or not math.isfinite(baseline) or not math.isfinite(current):
        return 0.0  # no usable baseline/sample -> no fatigue signal (fail-safe)
    delta = (current - baseline) if higher_is_fatigue else (baseline - current)
    return _clamp01(delta / baseline)


def mode_for_score(score: float) -> str:
    """Map a fatigue_score to a friction mode (§4), half-open [lo, hi):
    [0,0.4)->normal, [0.4,0.7)->caution, [0.7,0.9)->tired, [0.9,1.0]->exhausted."""
    if score < 0.4:
        return MODE_NORMAL
    if score < 0.7:
        return MODE_CAUTION
    if score < 0.9:
        return MODE_TIRED
    return MODE_EXHAUSTED


def score_and_mode(
    signals: Signals,
    weights: Weights = _DEFAULT_WEIGHTS,
    baseline_ready: bool = True,
) -> tuple[float, str]:
    """Slice-1 entrypoint. Weighted sum of the PRESENT signals (their weights
    renormalized to sum 1.0, §7), clamped to [0,1], mapped to a mode (§4).

    - baseline_ready=False -> mode forced to 'normal' (14-day calibration, §7) while
      the score is still computed.
    - missing/broken (None / NaN / inf) signals fail safe toward 'normal', never block
      (§8 autonomy invariant). All groups absent (weight sum 0) -> 'normal', no crash.
    - raises ValueError if the full weights do not sum to 1.0 (rejected loudly)."""
    total_w = weights.w_a + weights.w_b + weights.w_c
    if not math.isclose(total_w, 1.0, abs_tol=1e-9):
        raise ValueError(f"weights must sum to 1.0, got {total_w}")

    # Present groups only (None = absent for this tick); rescale their weights to 1.0.
    present = [
        (w, v)
        for w, v in (
            (weights.w_a, signals.input_delta),
            (weights.w_b, signals.temporal),
            (weights.w_c, signals.drift),
        )
        if v is not None
    ]

    # Fail-safe (§8, opposite of VAULT): no usable signal -> 'normal', never block.
    # Covers all-absent (weight sum 0) and any broken (NaN/inf) present value.
    present_w = sum(w for w, _ in present)
    if present_w == 0 or any(not math.isfinite(v) for _, v in present):
        return 0.0, MODE_NORMAL

    score = _clamp01(sum((w / present_w) * v for w, v in present))

    # Cold-start: force 'normal' during calibration, but the score is still computed.
    mode = MODE_NORMAL if not baseline_ready else mode_for_score(score)
    return score, mode


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))
