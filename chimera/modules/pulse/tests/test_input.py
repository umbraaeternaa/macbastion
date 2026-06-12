"""PULSE group-A mapper — MIRROR per-minute aggregates -> fatigue readings (PD-A-1).

MIRROR exposes only aggregate counters (privacy §8 — never raw input). This maps them
onto the three group-A signals assess() consumes. RED until pulse/input.py lands; pure."""

from pulse.input import input_signals


def test_normal_input_maps_all_three() -> None:
    sig = input_signals(chars=120, deletes=6, mouse_path_ratio=1.4)
    assert sig["typing_speed"] == 120.0
    assert sig["error_rate"] == 6 / 120
    assert sig["mouse_ineff"] == 1.4


def test_no_typing_omits_typing_signals() -> None:
    # 0 chars this minute = a pause, NOT gradely-slow typing -> typing signals ABSENT.
    sig = input_signals(chars=0, deletes=0, mouse_path_ratio=1.2)
    assert "typing_speed" not in sig
    assert "error_rate" not in sig
    assert sig["mouse_ineff"] == 1.2  # mouse still moved


def test_no_mouse_omits_mouse_signal() -> None:
    sig = input_signals(chars=100, deletes=2, mouse_path_ratio=None)
    assert "mouse_ineff" not in sig
    assert sig["typing_speed"] == 100.0
    assert sig["error_rate"] == 2 / 100


def test_error_rate_is_deletes_per_char() -> None:
    assert input_signals(chars=50, deletes=10, mouse_path_ratio=1.0)["error_rate"] == 0.2


def test_fully_idle_minute_is_empty() -> None:
    assert input_signals(chars=0, deletes=0, mouse_path_ratio=None) == {}
