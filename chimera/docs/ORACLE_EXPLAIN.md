# ORACLE Explainability — Design Record (#1)

> Design record. Builds on Mode B. ARCHITECTURE §5.3 authoritative; this records
> the explainability extension delivered in 819c1bb. Updated: 2026-06-04

---

## 1. Three layers (honest spec accounting)

- **Layer A — WITHIN §5.3.** A narrative `reasoning` string. This is exactly
  §2.1's intent: "Reasoning, not matching — the LLM explains *why* something is
  unusual, not just flags it." Not an extension; the spec asked for it.
- **Layer B — spec DEBT repaid.** `similar_events` is §5.3-defined
  (`oracle.classify` → `{score, reasoning, similar_events}`; `anomaly.detected`
  → `similar_past_events: top_3_baseline_matches`) but was deferred in the Mode B
  slice (MD-B-10a). Now implemented as **naive top-3 same source+type** from
  recent events. Proper embeddings-based similarity is still v2 (TODO).
- **Layer C — EXTENSION beyond §5.3.** §5.3 schematizes only a free-text
  `reasoning`. We add: `context_factors[]` (LLM-emitted short flags), derived
  prompt facts (`source_seen_before`, `type_seen_before`, `event_hour`,
  `hour_frequency`, `days_observed`), the `days_observed` baseline metric, and a
  prompt directive. This is a conscious extension, recorded here — not new spec.

---

## 2. Decisions (EP-1 … EP-9)

| ID | Area | Chosen | Rationale |
|----|------|--------|-----------|
| EP-1 | Output shape | (c) `{score, reasoning, context_factors[]}` | Narrative + flag list; `context_factors` optional/lenient (1B may omit → default []) |
| EP-2 | Method | (a) enrich existing `oracle.classify` | One path; no new API surface; classify and explanation inseparable |
| EP-3 | Prompt enrichment | (a)+(c) derived flags + directive | Explicit facts for a 1B model + guidance to cite them |
| EP-4 | similar_events | (a) naive top-3 same source+type now (+ embeddings TODO) | Repays the §5.3 debt cheaply; honest about naive similarity |
| EP-5 | Spec record | (a) this `docs/ORACLE_EXPLAIN.md` | Mirrors SHIM.md discipline; ARCHITECTURE stays untouched |
| EP-6 | Scope | (b) mid slice (context_factors + enrichment + similar) | Felt improvement without a new method/confidence |
| EP-7 | Testing | (a)+(c) prompt/schema structural (mock) + real-Ollama opt-in | Deterministic structure; real check without flaky text asserts |
| EP-8 | Invariant | (a) explicit advisory-only test | Locks "classify reads, never acts" against future change |
| EP-9 | days_observed | (a) distinct-day query | Adds the "over N days" signal; `record_event` untouched (Mode A) |

---

## 3. What `oracle.classify` returns now

```
{ score, reasoning, context_factors[], similar_events[] }
```

- `score` / `reasoning` — **strict** parse: malformed → INTERNAL_ERROR (MD-B-4a,
  no fake 0.5).
- `context_factors` — **LLM-emitted**, lenient parse: a missing/invalid array
  defaults to `[]` (EP-1 asymmetry; a 1B model may omit it).
- `similar_events` — **detector-computed** (deterministic): up to 3 recent events
  of the same `source`+`type`, as `{ts, source, type}` (payload omitted).

The detector also feeds derived facts into the prompt (`source_seen_before`,
`type_seen_before`, `event_hour`, `hour_frequency`, `days_observed`); `event.ts`
is optional, so hour factors degrade gracefully to `None` when absent.

---

## 4. Invariants held

- **advisory-only (D4).** `classify` returns text/data and never acts — no method
  mutates state or drives another module. Locked by `test_oracle_advisory.py`
  (classify does not change `event_count`).
- **local-first (MANIFESTO §1).** Derived facts come from the local baseline; the
  LLM is local llama3.2:1b. Zero network beyond localhost Ollama.

---

## 5. Testing approach

- **Deterministic:** prompt-structure (derived facts present in the prompt) and
  schema-shape (`RESPONSE_SCHEMA` has `context_factors`) with a mock LLM;
  `similar_events` asserted exactly (detector-computed).
- **NOT asserted:** the LLM's text (non-determinism even at temperature 0).
- **real-Ollama (`-m ollama`):** structural only — `score ∈ [0,1]`,
  `context_factors` is a list of strings, `similar_events` is a list.

---

## 6. Deferred (next slices)

- `oracle.explain` as a separate method — EP-2 chose to enrich `classify` instead.
- `confidence` field on the classification.
- Embeddings-based similarity — `similar_events` is currently naive recency.
- Auto-classify per event + `oracle.anomaly.detected` emission — a Mode B
  next-slice concern, separate from explainability (#1).

---

## 7. Status

Delivered in `819c1bb` (RED `672f84e` → GREEN). 527 tests total; `-m ollama`
green vs live llama3.2:1b; ruff + mypy --strict clean. ARCHITECTURE.md untouched.
