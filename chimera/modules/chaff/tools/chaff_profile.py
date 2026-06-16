#!/usr/bin/env python3
"""CHAFF Phase-A profiler (userspace, no root) — build a real decoy profile from the operator's
OWN browser history (Chromium: Chrome + Brave). Aggregates ONLY (category weights + hourly shape);
NEVER stores raw URLs (privacy, §8). Output: profile.json that CHAFF weights its decoys with,
replacing the flat equal-category pick. Honest scope: covers the CATEGORY + TEMPORAL axes; NOT
packet sizes / inter-request microtiming (those need privileged observation — still deferred)."""
from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from time import gmtime
from urllib.parse import urlparse

# CHAFF's fixed taxonomy (modules/chaff/data/endpoints.json + daemon.c CATEGORIES).
CATEGORIES = ("news", "tech", "social", "search", "dev")
CATMAP: dict[str, tuple[str, ...]] = {
    "news": ("bbc", "cnn", "nytimes", "reuters", "theguardian", "apnews", "npr", "bloomberg",
             "aljazeera", "washingtonpost", "pravda", "news"),
    "tech": ("arstechnica", "hackaday", "theverge", "wired", "techcrunch", "engadget",
             "tomshardware", "anandtech", "slashdot", "ixbt"),
    "social": ("twitter", "x.com", "facebook", "instagram", "mastodon", "reddit", "linkedin",
               "tiktok", "threads", "youtube", "telegram"),
    "search": ("google", "bing", "duckduckgo", "yandex", "ecosia", "startpage", "kagi",
               "search.brave"),
    "dev": ("github", "gitlab", "stackoverflow", "stackexchange", "npmjs", "pypi", "dev.to",
            "ycombinator", "gitea", "huggingface", "readthedocs", "developer.", "docs.",
            "zed.dev", "lovable"),
}
WEBKIT_EPOCH_OFFSET = 11644473600  # seconds between 1601-01-01 and 1970-01-01

CHROMIUM_DBS = [
    "~/Library/Application Support/Google/Chrome/Default/History",
    "~/Library/Application Support/BraveSoftware/Brave-Browser/Default/History",
]


def host_of(url: str) -> str:
    """netloc of a URL, lowercased, without a leading 'www.'."""
    h = (urlparse(url).netloc or "").lower()
    return h[4:] if h.startswith("www.") else h


def categorize(host: str, catmap: dict[str, tuple[str, ...]] = CATMAP) -> str | None:
    """Map a host to one of CHAFF's categories by keyword, or None if it fits none."""
    h = host.lower()
    for cat in CATEGORIES:  # deterministic order
        if any(k in h for k in catmap.get(cat, ())):
            return cat
    return None


def webkit_to_unix(micros: int) -> float:
    """Chromium last_visit_time (microseconds since 1601-01-01 UTC) -> unix seconds."""
    return micros / 1_000_000 - WEBKIT_EPOCH_OFFSET


def _normalize(d: dict[str, float]) -> dict[str, float]:
    tot = sum(d.values())
    return {k: (v / tot if tot else 1.0 / len(d)) for k, v in d.items()}


def build_profile(rows: list[tuple[str, int, int]]) -> dict[str, object]:
    """rows = [(url, visit_count, webkit_ts)] -> {categories: {cat: weight}, hourly: [24 weights],
    source_visits: N}. Category weights over CHAFF's 5 categories (uncategorised hosts ignored);
    hourly shape over all timestamped visits. Empty/zero -> flat (no-signal fallback)."""
    cats: dict[str, float] = dict.fromkeys(CATEGORIES, 0.0)
    hourly = [0.0] * 24
    visits = 0
    for url, vc, ts in rows:
        vc = max(0, int(vc))
        cat = categorize(host_of(url))
        if cat:
            cats[cat] += vc
        if ts:
            hr = gmtime(webkit_to_unix(ts)).tm_hour
            hourly[hr] += vc
        visits += vc
    htot = sum(hourly)
    cov = sum(cats.values()) / visits if visits else 0.0
    return {
        "categories": _normalize(cats),
        "hourly": [h / htot if htot else 1.0 / 24 for h in hourly],
        "source_visits": visits,
        "coverage": cov,  # fraction of visits that mapped to a CHAFF category
    }


def read_history(db_path: Path) -> list[tuple[str, int, int]]:
    """Copy the (possibly locked) history DB to a temp file and read (url, visit_count,
    last_visit_time). Returns [] on any failure (missing browser / locked / schema drift)."""
    if not db_path.exists():
        return []
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            tmp = Path(tf.name)
        shutil.copy2(db_path, tmp)
        con = sqlite3.connect(f"file:{tmp}?mode=ro", uri=True)
        rows = con.execute("select url, visit_count, last_visit_time from urls").fetchall()
        con.close()
        tmp.unlink(missing_ok=True)
        return [(str(u), int(v), int(t)) for u, v, t in rows]
    except Exception:
        return []


def main() -> int:
    rows: list[tuple[str, int, int]] = []
    for p in CHROMIUM_DBS:
        rows += read_history(Path(p).expanduser())
    profile = build_profile(rows)
    out = Path("~/.config/chimera/chaff/profile.json").expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(profile, indent=2))
    cats = profile["categories"]
    top = max(cats, key=lambda k: cats[k]) if isinstance(cats, dict) and cats else "n/a"
    print(f"chaff_profile: {profile['source_visits']} visits -> {out} (top category: {top})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
