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

- More queries: `trend` (per-day bucket), `compare` (periodA vs periodB),
  `new_since(cutoff)`.
- `oracle.baseline.export` — the §5.3 spec-debt (TM-9b).

---

## 8. Layer 2 — Conversational NL ask (delivered 2feaf67)

### Architecture (two-step, one LLM call)

- `oracle.ask(question)` → `Asker(llm, timemachine)`.
- **Step 1 (LLM):** intent extraction — question → `{query_type enum, params}` via
  `format=INTENT_SCHEMA`.
- **Step 2 (code):** validate params per type → dispatch the Layer 1 query
  (deterministic).
- **Step 3 (code):** code-templated answer (NL-2a — NO LLM narration this
  sub-slice).
- Asker **composes** TimeMachine — Layer 1 stays LLM-free (its 10 tests intact).

### Return shape

`oracle.ask` → `{answer, query_used, raw_result}`
- `answer` — code-templated human sentence (deterministic).
- `query_used` — which query the LLM chose (transparency).
- `raw_result` — verbatim Layer 1 result (the safeguard, see limitation below).

### Honest limitation — enum stops invented queries, NOT semantic mis-routing

The INTENT_SCHEMA enum (`query_type ∈ {first_seen, period, unknown}`) prevents the
LLM inventing a nonexistent query — but it can still choose the WRONG allowed
query or hallucinate params. Empirical: asked "when did chaff first appear?",
llama3.2:1b returned `source="whatsapp"` (query_type right, source hallucinated).
`raw_result` is the transparent safeguard — the caller sees exactly what ran.
`ask` is best-effort NL, not a correctness guarantee.

### "unknown" fallback (NL-4a)

A 1B model is often uncertain. Malformed / unsure / invalid-params →
`query_used="unknown"` + an honest "couldn't map" answer (lenient parse —
asymmetric with Mode B's strict parse by design; an honest don't-know beats
guessing).

### core timeout (NL-12a, data-driven)

Measured: a cold `llama3.2:1b` intent call is ~4.4s; the 5s default is too tight
→ `core/server.py` METHOD_TIMEOUTS gains `oracle.ask: 15.0` (< classify's 30s —
intent is lighter).

### Decisions (NL-1 … NL-12)

| ID | Area | Chosen | Rationale |
|----|------|--------|-----------|
| NL-1 | Routing | (b) structured intent (query_type enum) | enum forbids inventing a query; dispatch deterministic |
| NL-2 | LLM calls | (a) one (intent) + code-templated answer | Deterministic answer; narration deferred |
| NL-3 | Intent schema | (a) flat {query_type, source?, event_type?, start?, end?} | Simple for a 1B model |
| NL-4 | Unsure/unknown | (a) "unknown" enum → honest "don't know" | Beats guessing the wrong query |
| NL-5 | Param validation | (a) per-type before dispatch | LLM garbage → unknown, not a junk query |
| NL-6 | Return shape | (a) {answer, query_used, raw_result} | Transparent + deterministic raw_result safeguard |
| NL-7 | Gate | (a) -31004 when Ollama down | Consistent with Mode B |
| NL-8 | Testing | (a)+(b) mock intent exact + real-Ollama structural | Deterministic routing tests; real call structural-only |
| NL-9 | Component | (a) new ask.py Asker(llm, timemachine) | Keeps Layer 1 LLM-free |
| NL-10 | Spec record | (a) this Layer 2 section | Mirrors the doc's discipline |
| NL-11 | Scope | (c) intent-only on first_seen + period | Routing tested; narration a later sub-slice |
| NL-12 | core timeout | (a) oracle.ask: 15.0 | Data-driven (cold ~4.4s vs 5s default) |

### Layer 2 deferred (next sub-slice)

- **LLM narration** — a richer human answer vs the code-template; re-check the
  timeout if a second LLM call is added.
- `trend` / `compare` / `new_since` routing — needs those Layer 1 queries first.

---

## 9. Status

Layer 1 delivered in `8522c87`; Layer 2 (NL ask) delivered in `2feaf67`
(RED `9de26a0` → GREEN). 548 tests total; ruff + mypy --strict clean.
ARCHITECTURE.md untouched.
