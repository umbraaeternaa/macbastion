"""PULSE scoring engine (§5.5, slice 1) — RED.

Hermetic: every test feeds already-normalized signals + a baseline snapshot; nothing
touches MIRROR/ORACLE/SQLite/hardware. Fail-safe direction is asserted EXPLICITLY —
broken/missing signals must degrade to 'normal' (less friction), never block (§8).
"""

import math

import pytest
from pulse.scoring import (
    MODE_CAUTION,
    MODE_EXHAUSTED,
    MODE_NORMAL,
    MODE_TIRED,
    Signals,
    Weights,
    mode_for_score,
    normalize_delta,
    score_and_mode,
)

# --- §4 friction modes, half-open [lo, hi) (boundary owned by the upper band) ---


def test_mode_normal_at_zero():
    assert mode_for_score(0.0) == MODE_NORMAL


def test_mode_normal_just_below_0_4():
    assert mode_for_score(0.39) == MODE_NORMAL


def test_mode_caution_at_0_4_boundary():
    assert mode_for_score(0.4) == MODE_CAUTION


def test_mode_caution_just_below_0_7():
    assert mode_for_score(0.69) == MODE_CAUTION


def test_mode_tired_at_0_7_boundary():
    assert mode_for_score(0.7) == MODE_TIRED


def test_mode_tired_just_below_0_9():
    assert mode_for_score(0.89) == MODE_TIRED


def test_mode_exhausted_at_0_9_boundary():
    assert mode_for_score(0.9) == MODE_EXHAUSTED


def test_mode_exhausted_at_one():
    assert mode_for_score(1.0) == MODE_EXHAUSTED


# --- §3 weighted sum with default weights (0.55 / 0.30 / 0.15) ---


def test_weighted_sum_default_weights():
    # 0.55*0.8 + 0.30*0.5 + 0.15*0.2 = 0.44 + 0.15 + 0.03 = 0.62
    score, mode = score_and_mode(Signals(input_delta=0.8, temporal=0.5, drift=0.2))
    assert score == pytest.approx(0.62)
    assert mode == MODE_CAUTION


# --- §7 renormalization of present groups to sum 1.0 ---


def test_renorm_oracle_off_rescales_a_b():
    # drift None -> w_a, w_b rescale to sum 1: 0.55/0.85 and 0.30/0.85.
    # input=1.0, temporal=0.0 -> score = 0.55/0.85 ≈ 0.647
    score, mode = score_and_mode(Signals(input_delta=1.0, temporal=0.0, drift=None))
    assert score == pytest.approx(0.55 / 0.85)
    assert mode == MODE_CAUTION


def test_renorm_mirror_off_temporal_only():
    # input None and drift None -> temporal-only, w_b rescales to 1.0
    score, mode = score_and_mode(Signals(input_delta=None, temporal=0.8, drift=None))
    assert score == pytest.approx(0.8)
    assert mode == MODE_TIRED  # 0.8 in [0.7, 0.9)


def test_renorm_both_off_failsafe_normal():
    # all groups absent -> weight sum 0 (edge) -> fail-safe 'normal', no crash
    _score, mode = score_and_mode(Signals(input_delta=None, temporal=None, drift=None))
    assert mode == MODE_NORMAL


# --- §7 cold-start calibration: baseline not ready -> normal, but score is computed ---


def test_baseline_not_ready_forces_normal_but_still_scores():
    score, mode = score_and_mode(
        Signals(input_delta=1.0, temporal=1.0, drift=1.0), baseline_ready=False
    )
    assert mode == MODE_NORMAL
    assert score == pytest.approx(1.0)  # score still computed for silent baselining


# --- §8 fail-safe (OPPOSITE of VAULT): broken signal -> normal, never block ---


def test_failsafe_nan_signal_yields_normal():
    _score, mode = score_and_mode(
        Signals(input_delta=math.nan, temporal=0.5, drift=0.2)
    )
    assert mode == MODE_NORMAL


def test_failsafe_inf_never_escalates_to_block():
    # an inf signal must neither crash nor push the operator into exhausted/block
    _score, mode = score_and_mode(
        Signals(input_delta=math.inf, temporal=0.0, drift=0.0)
    )
    assert mode == MODE_NORMAL


# --- weights validation: full set must sum to 1.0, rejected loudly ---


def test_weights_not_summing_to_one_rejected():
    with pytest.raises(ValueError):
        score_and_mode(
            Signals(input_delta=0.5, temporal=0.5, drift=0.5),
            weights=Weights(w_a=0.5, w_b=0.3, w_c=0.3),  # sum 1.1
        )


# --- score clamping to [0, 1] ---


def test_score_clamped_to_one():
    score, mode = score_and_mode(Signals(input_delta=2.0, temporal=1.0, drift=1.0))
    assert score == pytest.approx(1.0)
    assert mode == MODE_EXHAUSTED


def test_score_clamped_to_zero():
    score, mode = score_and_mode(Signals(input_delta=-1.0, temporal=0.0, drift=0.0))
    assert score == pytest.approx(0.0)
    assert mode == MODE_NORMAL


# --- §3 group A delta normalization, both fatigue directions ---


def test_normalize_delta_higher_is_fatigue():
    # delete rate: current 1.5x baseline -> (0.5b)/b = 0.5
    assert normalize_delta(1.5, 1.0, higher_is_fatigue=True) == pytest.approx(0.5)


def test_normalize_delta_lower_is_fatigue():
    # typing speed: current 0.5x baseline (slower) -> (0.5b)/b = 0.5
    assert normalize_delta(0.5, 1.0, higher_is_fatigue=False) == pytest.approx(0.5)


def test_normalize_delta_clamps_to_one():
    assert normalize_delta(3.0, 1.0, higher_is_fatigue=True) == pytest.approx(1.0)


def test_normalize_delta_non_fatigue_direction_is_zero():
    # faster than baseline when slower-is-fatigue -> 0, never negative
    assert normalize_delta(2.0, 1.0, higher_is_fatigue=False) == pytest.approx(0.0)
