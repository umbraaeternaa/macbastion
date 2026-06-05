# ORACLE Behavioral Time-Machine — Design Record (#2)

> Design record. Builds on Mode B + explainability. ARCHITECTURE §5.3
> authoritative; this records the time-machine extension delivered in 8522c87.
> Updated: 2026-06-04

---

## 1. Two layers (honest spec accounting)

- **Layer A — spec DEBT (deferred).** `oracle.baseline.export` is §5.3-defined
  (`none` → `{baseline_summary}` sanitized) but NOT implemented. Deferred to a
  separate slice (TM-9b) — not part of this work.
- **Layer B — EXTENSION beyond §5.3.** Structured time-range queries
  (`first_seen`, `period`) are wholly new — §5.3 has no query / trend /
  time-range / comparison concept ("queryable" there refers to SQLite, not an
  exposed API). A conscious extension, recorded here (not new spec).

---

## 2. Decisions (TM-1 … TM-11)

| ID | Area | Chosen | Rationale |
|----|------|--------|-----------|
| TM-1 | Architecture | (c) hybrid — but this slice ships Layer 1 only (structured; LLM deferred) | Deterministic data now; conversational NL layer later |
| TM-2 | Methods | (a) `oracle.query.*` family | Clean, extensible namespace |
| TM-3 | Query set | (a) `first_seen` + `period` | Two primitives — smallest useful set |
| TM-4 | DB access | (a)+(c) SQL in baseline.py; TimeMachine orchestrates | Encapsulation — query.py never touches store._con |
| TM-5 | LLM role | (a) none this slice | Fully deterministic; zero non-determinism |
| TM-6 | Spec record | (a) this `docs/ORACLE_TIMEMACHINE.md` | Mirrors ORACLE_EXPLAIN/SHIM; ARCHITECTURE untouched |
| TM-7 | Testing | (a) structured exact (seed ts → assert) | Deterministic; no LLM to mock |
| TM-8 | Scope | (a) smallest — first_seen + period, no LLM/NL | Small RED, useful on its own |
| TM-9 | baseline.export | (b) deferred (separate slice) | Keeps #2 focused on time-range |
| TM-10 | Invariant | (a) advisory-only read-only test | Locks "queries never mutate" |
| TM-11 | Boundaries | (a) ISO-8601 lexicographic, half-open [start, end) | No parsing; no double-count on shared boundary |

---

## 3. What `oracle.query.*` returns now (Layer 1 — deterministic, no LLM)

```
oracle.query.first_seen(source, event_type=None)
  → {source, event_type, first_seen: ts | None}

oracle.query.period(start, end)
  → {start, end, total, by_source, by_type}
```

- `first_seen` — earliest `ts` (`MIN`) for the source (optionally a type); `None`
  if never seen.
- `period` — counts in the **half-open** window `[start, end)`: an event on
  `start` is included, an event on `end` is excluded (no double-count across
  adjacent periods).
- ISO-8601 lexicographic comparison — no datetime parsing (the observer writes
  `datetime.now(UTC).isoformat()`).

---

## 4. Architecture

- `query.py` `TimeMachine` orchestrates: validates inputs (in the client
  handlers), shapes responses, off-loads the blocking store calls via
  `asyncio.to_thread`. It **never touches `store._con`**.
- The SQL lives in `baseline.py` (`first_seen` = `MIN(ts)`; `period_summary` =
  `COUNT` / `GROUP BY` over `[start, end)`), which owns the connection + lock.
- Mirrors the detector(orchestrate) ↔ baseline(data) split.

---

## 5. Invariants held

- **advisory-only.** Queries are read-only `SELECT`s — they never act or mutate.
  Locked by `test_oracle_advisory.py` (a query leaves `event_count` unchanged).
- **local-first (MANIFESTO §1).** SQL runs on the local baseline; zero network;
  no LLM in this layer.

---

## 6. Testing

- Structured exact: seed events with known `ts`, assert `first_seen` / `period`
  counts precisely.
- Fully deterministic — no LLM this slice, so no `-m ollama` and no
  non-determinism to manage.

---

## 7. Deferred (next slices)

- **Layer 2 — conversational.** `oracle.ask(NL)` + LLM narration of query
  results (the non-deterministic layer, split off deliberately).
- More queries: `trend` (per-day bucket), `compare` (periodA vs periodB),
  `new_since(cutoff)`.
- `oracle.baseline.export` — the §5.3 spec-debt (TM-9b).

---

## 8. Status

Delivered in `8522c87` (RED `dc80bc2` → GREEN). 537 tests total; ruff + mypy
--strict clean. ARCHITECTURE.md untouched.
