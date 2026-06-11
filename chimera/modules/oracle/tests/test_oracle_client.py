"""Unit: OracleClient emit-side — anomaly emission on classify (idea #3, 3C).

Hermetic: a fake detector supplies the score (no Ollama), and a FakeWriter stands
in for the shared command writer so we can read the frames ORACLE emits. The emit
lives in the CLIENT (_handle_classify), NOT the detector — the detector stays
advisory-pure (Mode B + advisory tests untouched).

advisory (D4): oracle.anomaly.detected is a NOTIFICATION — ORACLE announces, it
never acts. Core (3B relay) routes it; ORACLE never calls another module.

RED: _handle_classify does not emit yet — the high-score test fails (no frame);
the low-score and contract tests pass (no emit either way / classify returns the
same result).
"""

from typing import Any

from core.envelope import Notification, parse
from oracle.baseline import BaselineStore
from oracle.client import OracleClient


class FakeDetector:
    """Detector stand-in with a fixed score (no Ollama). Separate from the 0.42
    FakeDetector in test_oracle_integration — high/low score drives the threshold."""

    def __init__(self, score: float, threshold: float = 0.7) -> None:
        self._score = score
        self._threshold = threshold

    async def classify(self, event: dict[str, Any]) -> dict[str, Any]:
        return {
            "score": self._score,
            "reasoning": "suspicious" if self._score >= self._threshold else "normal",
            "context_factors": [],
            "similar_events": [],
        }

    def get_threshold(self) -> float:
        return self._threshold

    def set_threshold(self, value: float) -> dict[str, Any]:
        return {"threshold": value}


class FakeWriter:
    """Captures frames written to the shared command writer (no socket)."""

    def __init__(self) -> None:
        self._chunks: list[bytes] = []

    def write(self, data: bytes) -> None:
        self._chunks.append(data)

    async def drain(self) -> None:
        return None

    def frames(self) -> list[str]:
        return b"".join(self._chunks).decode().splitlines()


def _make_client(tmp_path: Any, score: float) -> OracleClient:
    store = BaselineStore(tmp_path / "b.db", tmp_path / "b.key")
    client = OracleClient(tmp_path, store, detector=FakeDetector(score))
    client._cmd_writer = FakeWriter()  # type: ignore[assignment]
    return client


def _anomalies(client: OracleClient) -> list[Notification]:
    frames = client._cmd_writer.frames()  # type: ignore[union-attr]
    notes = [parse(f) for f in frames]
    return [
        m
        for m in notes
        if isinstance(m, Notification) and m.method == "oracle.anomaly.detected"
    ]


_EVENT = {"event": {"source": "chaff", "type": "request.sent"}}


# A — high score (>= threshold) emits oracle.anomaly.detected with the advisory
#     payload {score, threshold, source, type, reasoning}.
async def test_classify_high_score_emits_anomaly(tmp_path: Any) -> None:
    client = _make_client(tmp_path, score=0.95)
    await client._handle_classify(_EVENT)
    anomalies = _anomalies(client)
    assert len(anomalies) == 1
    p = anomalies[0].params
    assert isinstance(p, dict)
    assert p["score"] == 0.95
    assert p["threshold"] == 0.7
    assert p["source"] == "chaff"
    assert p["type"] == "request.sent"
    assert "reasoning" in p


# B — low score (< threshold) emits nothing.
async def test_classify_low_score_no_emit(tmp_path: Any) -> None:
    client = _make_client(tmp_path, score=0.1)
    await client._handle_classify(_EVENT)
    assert _anomalies(client) == []


# C — the classify contract is unchanged: it still returns {score, reasoning, ...}
#     regardless of whether an anomaly is emitted (emit is additive).
async def test_classify_contract_unchanged(tmp_path: Any) -> None:
    client = _make_client(tmp_path, score=0.95)
    result = await client._handle_classify(_EVENT)
    assert result["score"] == 0.95
    assert result["reasoning"] == "suspicious"


def _cleared(client: OracleClient) -> list[Notification]:
    frames = client._cmd_writer.frames()  # type: ignore[union-attr]
    notes = [parse(f) for f in frames]
    return [
        m
        for m in notes
        if isinstance(m, Notification) and m.method == "oracle.anomaly.cleared"
    ]


# D — symmetric all-clear: once anomalous (score crossed up through the threshold),
#     a later score dropping below the hysteresis band emits oracle.anomaly.cleared
#     ONCE, with the symmetric advisory payload. ORACLE is now bidirectional.
async def test_anomalous_then_low_emits_cleared(tmp_path: Any) -> None:
    client = _make_client(tmp_path, score=0.95)
    await client._handle_classify(_EVENT)  # cross up -> detected, now anomalous
    client._detector._score = 0.4  # type: ignore[union-attr]  # well below the band
    await client._handle_classify(_EVENT)  # cross down -> cleared
    cleared = _cleared(client)
    assert len(cleared) == 1
    p = cleared[0].params
    assert isinstance(p, dict)
    assert p["score"] == 0.4
    assert p["threshold"] == 0.7
    assert p["source"] == "chaff"
    assert p["type"] == "request.sent"


# E — hysteresis holds: after an anomaly, a score that dips below the threshold but
#     stays INSIDE the band (threshold - margin) does NOT clear — no flapping.
async def test_in_band_does_not_clear(tmp_path: Any) -> None:
    client = _make_client(tmp_path, score=0.95)
    await client._handle_classify(_EVENT)  # anomalous
    client._detector._score = 0.65  # type: ignore[union-attr]  # < 0.7 but inside the band
    await client._handle_classify(_EVENT)
    assert _cleared(client) == []


# F — no clear from a cold start: a low score when never anomalous emits nothing
#     (neither detected nor cleared).
async def test_cold_low_does_not_clear(tmp_path: Any) -> None:
    client = _make_client(tmp_path, score=0.1)
    await client._handle_classify(_EVENT)
    assert _cleared(client) == []
    assert _anomalies(client) == []
