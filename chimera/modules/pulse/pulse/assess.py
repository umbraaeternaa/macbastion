"""PULSE assessment — wires the baseline store to the scoring engine
(§5.5, slice 3 / WS-1…WS-7).

Bridges the two existing halves: for each present group-A signal it pulls the 14-day
baseline from the store, normalizes the current reading against it (normalize_delta,
fatigue direction per GROUP_A_DIRECTIONS), composes group A into ONE input_delta (mean
of present sub-deltas, WS-3), then builds Signals and calls score_and_mode. temporal
(group B) and drift (group C) are caller-supplied here — their live producers (kqueue
idle, ORACLE drift) are deferred.

Group-A contract (WS-2, the PULSE side of gap D8, per spec §3): name -> higher_is_fatigue.
The VALUES are caller-supplied (the daemon later maps MIRROR aggregates onto these names),
so assess stays decoupled from MIRROR's wire format. `now` is an injected ISO string.
"""

from __future__ import annotations

from pulse.baseline import BaselineStore
from pulse.scoring import Signals, Weights, normalize_delta, score_and_mode

# Group-A signal directions (WS-2, per §3): is a higher reading more fatigue?
GROUP_A_DIRECTIONS = {
    "typing_speed": False,  # slower than baseline = fatigue
    "error_rate": True,     # more deletes per char = fatigue
    "mouse_ineff": True,    # longer path for the same target = fatigue
}

_DEFAULT_WEIGHTS = Weights()


def _group_a_delta(
    store: BaselineStore, now: str, group_a: dict[str, float] | None
) -> float | None:
    """Mean of the present group-A sub-deltas (WS-3); None if no group-A signal has
    both a current reading and a usable baseline (-> group A absent for this tick)."""
    if not group_a:
        return None
    deltas: list[float] = []
    for name, higher_is_fatigue in GROUP_A_DIRECTIONS.items():
        current = group_a.get(name)
        if current is None:
            continue
        baseline = store.baseline(name, now)
        if baseline is None:
            continue  # cold signal — no baseline yet, skip (WS-4)
        deltas.append(normalize_delta(current, baseline, higher_is_fatigue))
    if not deltas:
        return None
    return sum(deltas) / len(deltas)


def assess(
    store: BaselineStore,
    now: str,
    *,
    group_a: dict[str, float] | None = None,
    temporal: float | None = None,
    drift: float | None = None,
    weights: Weights = _DEFAULT_WEIGHTS,
) -> tuple[float, str]:
    """Compute (fatigue_score, mode) from current readings + the baseline store.

    group A -> per-signal normalize_delta vs the store baseline -> mean = input_delta
    (None if no group-A signal has a usable baseline); temporal/drift passed through;
    mode frozen to 'normal' until store.baseline_ready(now). Fail-safe is inherited
    from score_and_mode (broken/all-absent -> 'normal', never block; §8).
    """
    signals = Signals(
        input_delta=_group_a_delta(store, now, group_a),
        temporal=temporal,
        drift=drift,
    )
    return score_and_mode(signals, weights, baseline_ready=store.baseline_ready(now))
