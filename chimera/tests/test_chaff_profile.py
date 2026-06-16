"""Hermetic tests for the CHAFF Phase-A profiler pure logic (modules/chaff/tools/chaff_profile.py).
The DB read (read_history/main) is manual-tier; the categorisation + aggregation are tested."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "modules" / "chaff" / "tools"))

import chaff_profile as cp  # noqa: E402

WEBKIT_EPOCH = cp.WEBKIT_EPOCH_OFFSET * 1_000_000  # webkit micros for unix epoch 0


def test_host_of_strips_www_and_lowercases():
    assert cp.host_of("https://www.BBC.com/news") == "bbc.com"
    assert cp.host_of("https://github.com/u/r") == "github.com"


def test_categorize_maps_known_and_rejects_unknown():
    assert cp.categorize("bbc.com") == "news"
    assert cp.categorize("arstechnica.com") == "tech"
    assert cp.categorize("twitter.com") == "social"
    assert cp.categorize("google.com") == "search"
    assert cp.categorize("github.com") == "dev"
    assert cp.categorize("some-random-blog.org") is None


def test_webkit_to_unix_epoch():
    assert cp.webkit_to_unix(WEBKIT_EPOCH) == 0.0  # exactly the unix epoch


def test_build_profile_weights_and_hourly():
    rows = [
        ("https://bbc.com/x", 3, WEBKIT_EPOCH),       # news, hour 0 (UTC)
        ("https://github.com/y", 7, WEBKIT_EPOCH),    # dev,  hour 0
        ("https://some-random.org/z", 5, WEBKIT_EPOCH),  # uncategorised -> ignored in cats
    ]
    p = cp.build_profile(rows)
    assert abs(p["categories"]["dev"] - 0.7) < 1e-9
    assert abs(p["categories"]["news"] - 0.3) < 1e-9
    assert p["categories"]["tech"] == 0.0
    assert abs(sum(p["categories"].values()) - 1.0) < 1e-9
    assert abs(sum(p["hourly"]) - 1.0) < 1e-9
    assert abs(p["hourly"][0] - 1.0) < 1e-9  # all visits landed in UTC hour 0
    assert p["source_visits"] == 15
    assert abs(p["coverage"] - 10 / 15) < 1e-9  # 10 of 15 visits categorised (news+dev)


def test_build_profile_empty_is_flat_fallback():
    p = cp.build_profile([])
    assert all(abs(w - 0.2) < 1e-9 for w in p["categories"].values())  # 1/5 flat
    assert abs(sum(p["hourly"]) - 1.0) < 1e-9
    assert p["source_visits"] == 0
    assert p["coverage"] == 0.0
