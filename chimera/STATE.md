# CHIMERA — Project State Snapshot

> Updated: 2026-06-05
> Version: 0.1.0-alpha (genesis)

---

## Completed module specifications

| Module | Lang  | Commit    | Notes                          |
|--------|-------|-----------|--------------------------------|
| CHAFF  | C     | `e0c8116` | §5.1 — background traffic gen  |
| ECHO   | C     | `a64f7d9` | §5.2                           |
| ORACLE | Py    | `2f753cb` | §5.3 — local LLM anomaly detect|
| MIRROR | C     | `a951c92` | §5.4 — behavioral noise inject |
| PULSE  | C+Py  | `5f5b64a` | §5.5 — cognitive load monitor  |
| VAULT  | C     | `1fdc517` | §5.6 — time-locked storage     |
| TETHER | C++   | `3b5fca9` | §5.7 — proximity dead-man      |
| PURGE  | C+Asm | `4a3c9df` | §5.8 — secure erasure (panic)  |

All 8 of 8 module specifications complete. Part 2 (§5) closed.

Genesis commit (manifesto + architecture Part 1): `f229751`

## Completed design records

| Record | Commit    | Notes                                            |
|--------|-----------|--------------------------------------------------|
| UX     | `cb10247` | UX surface decision — CLI + swiftbar + event stream (`chimera/docs/UX.md`) |
| OPSEC  | `a3ae3ad` | Operator security discipline — companion to §8 (`chimera/docs/OPSEC.md`) |
| SHIM   | `7092f8e` | Privileged shim decisions SH-1…12 + secret-handoff SS-0…7 + SH-5 staged amendment (`chimera/docs/SHIM.md`) |
| ORACLE_EXPLAIN | `ea10e5e` | Explainability design EP-1…9 (`chimera/docs/ORACLE_EXPLAIN.md`) |
| ORACLE_TIMEMACHINE | `e1c3cbc` | Time-machine design TM-1…11 (`chimera/docs/ORACLE_TIMEMACHINE.md`) |

---

## ARCHITECTURE.md progress

Last completed section: **§8** (Part 5 of 5). Part 1 (§1–§4) also complete.

Done:
- §5 — Detailed module specs (Part 2) — **DONE** (8/8: `4a3c9df` closes it)
- §6 — IPC protocol: JSON-RPC schemas (Part 3) — **DONE** (`3daa138`)
- §7 — Module lifecycle (Part 4) — **DONE** (`1863057`)
- §8 — Security model (Part 5) — **DONE** (`52477fe`)

---

## Specification phase: COMPLETE

As of 2026-05-28, the CHIMERA specification phase is closed. §8 closes it:
the architectural document is whole and authoritative. No spec work remains.

- **ARCHITECTURE.md** — all five parts: §1–§4 (concept, stack, principles),
  §5 (modules), §6 (IPC), §7 (lifecycle), §8 (security model)
- **Module specs** — 8 of 8 (CHAFF, ECHO, ORACLE, MIRROR, PULSE, VAULT, TETHER, PURGE)
- **7 design documents total** — 5 ARCHITECTURE parts + UX.md + OPSEC.md

**Next — code phase begins:**
- Core skeleton, targeted at chimera **v0.2.0** — socket server, router, broker,
  registry, capability-token issuer, privileged shim

---

## Code status

Code phase: all 8 core modules implemented (ETAP 2 closed). ETAP 3 underway —
Step 0 (CHAFF spec align), Step 1A (config request_timeout_s), Step 1B
(Router 4A), Step 2 (CHAFF: 2A bootstrap, 2B RED, 2C GREEN, 2D daemon + integration),
MIRROR (bootstrap, RED, engine GREEN, daemon wiring), ORACLE (RED, observe-first
GREEN, Mode B GREEN, explainability GREEN, time-machine GREEN) done. Privileged
shim (trust-plane, NOT an organ): Slice 1 NO-OP skeleton (RED→GREEN) done.
Last completed: **shim Slice 1 NO-OP skeleton** (commit `e60e8ae`) — the
privileged trust-plane's first slice: UNIX socket SERVER + LOCAL_PEERCRED peer
auth (peercred-only, SS-6, no secret) + 4-op enum whitelist (lock/evict/reboot/
killall — ALL no-op, F3, ZERO destructive effect) + ping/pong; CHIMERA §6 error
codes (-31007 wrong-uid auth-first, -31002 unknown op); shim.* namespace; C17
strict -Werror. ownership_apply = documented-stub (real chmod 0660 + chown
root:group is a -m privileged follow-up). Secret handshake = Slice 2 (gated on
code-signing, §5.5); real ops = Slice 3+ (destructive last). Design in
docs/SHIM.md (SS-0…7 + SH-5 staged amendment).

**Skeleton scope check (MANIFESTO §4 — honest accounting):**

Core skeleton v0.2.0 (§7.12) lists: socket server, router, broker, registry,
capability-token issuer, AND a privileged shim (§7.10 / §8.8 — a separate
C/LaunchDaemon for elevated operations, not among the 8 Python `core/` modules).

- Python `core/`: 8/8 modules done ✓
- Privileged shim: Slice 1 NO-OP skeleton done ✓ (peercred-only; secret = Slice 2 gated on code-signing, real ops = Slice 3+)

**ETAP 2 verdict:** Python core skeleton complete. The privileged shim is a
prerequisite for native modules requiring elevated capabilities (VAULT, PURGE,
etc.); its Slice 1 NO-OP skeleton is now done (`e60e8ae`), with the per-boot
secret (Slice 2) gated on code-signing (§5.5) and real ops deferred to Slice 3+.

**`chimera/core/` — 8 of 8 modules implemented:**
- `errors` (§6.5) — JSON-RPC + CHIMERA error codes, RpcError — DONE (`f284891`)
- `envelope` (§6.4) — JSON-RPC 2.0 wire format, parse/serialize, NDJSON — DONE (`6ed8e77`)
- `config` (§6.3, §7, §8) — CoreConfig: paths, defaults, env > toml > defaults hierarchy — DONE (`a6eed2a`)
- `tokens` (§6.9, §8.6 I6) — TokenIssuer: HMAC-SHA256 capability tokens, in-RAM key — DONE (`f9fa508`)
- `broker` (§6.6 + §6.8) — EventBroker: async pub/sub, wildcard topics, drop-oldest backpressure — DONE (`b63916c`)
- `lifecycle` (§7.2 + §7.4 + §7.5) — Lifecycle: 9-state FSM, 16-edge allow-list, heartbeat sweep, restart policy — DONE (`57a99fd`)
- `registry` (§6.7 + §7.2) — Registry: capability store, composes+drives Lifecycle, prefix-split matching, register/deregister events — DONE (`e4a10ba`)
- `server` (§6.3 + §6.2 + §6.9) — Server: two UNIX sockets, core.* dispatch + 4A module routing (internal-id correlation, per-method timeouts, fail-closed), 3B token reissue, event push, graceful shutdown — DONE (`33f2d38`; 4A routing `06bf7cb`)

No scaffold remains — all 8 core modules implemented.

**Native modules (`chimera/modules/`) — 3 of 8 started:**
- `chaff` (§5.1) — first native module, working daemon. C17 + ARM64 (Make +
  vendored Unity/cJSON); connects to core, registers + heartbeats, serves chaff.*
  via the 4A router, emits events, generates decoy HTTPS traffic (two pthread
  threads, poll-based IPC, openssl Fernet, SQLite). 46 Unity + 4 integration
  (hermetic). binary -Werror clean. Phase A (profiling) deferred to the
  privileged shim (pf/dtrace = root). — Phase B daemon DONE (`4f443f5`)
- `mirror` (§5.4) — second native module, working daemon. C17 (Make + vendored
  Unity/cJSON, frameworks only — no curl/sqlite/openssl). Connects to core,
  registers (8 methods, 2 events, depends_on=[]), serves mirror.* via the 4A
  router, heartbeats — single inline IPC loop (no pthread; the would-be 2nd
  thread is the gated tap). Engine: Box-Muller gaussian mouse noise, uniform
  timing jitter (clamp ≥0), §3 presets (light/medium/heavy), secure-field
  downgrade to light, fixed-capacity exclusion list, cumulative per-event-type
  stats (§7 — counts only). Config: MIRROR_CONFIG_PATH, non-fatal (defaults if
  missing/malformed). 42 Unity + 4 integration. binary -Werror clean. ipc/jsonrpc
  copied from chaff (D1=C). CGEventTap install + event emission STILL gated
  (code-signing + Accessibility TCC, §6/§9); mirror.enable → -31004; no event
  producer yet (drain_events seam wired, queue empty). — daemon GREEN (`41ef5b1`)
- `oracle` (§5.3) — third native module, FIRST Python module (CHAFF/MIRROR are
  C). observe-first slice: dual-role daemon — conn #1 core.sock (registers,
  serves oracle.{status,observe} via the 4A router, heartbeats, emits
  oracle.baseline.updated) + conn #2 events.sock (core.subscribe chaff.*, D5=b
  allow-list; push-loop into the Observer). One asyncio loop under a TaskGroup;
  shared command writer guarded by an asyncio.Lock. Observer = Mode A learning +
  D11 self-loop guard (oracle.* ignored). BaselineStore = SQLite (events +
  baseline_meta) + Fernet (payload/ctx encrypted at rest), thread-safe
  (check_same_thread=False + RLock), blocking writes off-loaded via
  asyncio.to_thread. advisory-only (D4): no acting methods. Mode B: oracle.classify
  + oracle.threshold.set via 4A run a real local LLM (llama3.2:1b Q8_0 via Ollama)
  with structured output (format=schema); detector.py + llm.py + prompt.py; context
  = recent_events + summary (baseline-aware); D6 gate (-31004 if Ollama down, Mode A
  survives); malformed → INTERNAL_ERROR (no fake 0.5); threshold meta-backed (0.7);
  status.model from startup probe; classifications_today in-memory. Explainability
  (#1): classify returns {score, reasoning, context_factors[] (LLM-emitted),
  similar_events[] (naive top-3, §5.3 debt repaid)}; derived prompt facts
  (source/type-seen, hour_freq, days_observed) + directive; advisory invariant test.
  Time-Machine (#2): Layer 1 — oracle.query.first_seen + oracle.query.period
  (structured time-range, deterministic, no LLM; query.py TimeMachine, SQL in
  baseline, half-open [start, end)). Layer 2 — oracle.ask: enum-constrained LLM
  intent → dispatch Layer 1 → code-templated {answer, query_used, raw_result};
  "unknown" fallback; raw_result safeguard; ask.py Asker composes TimeMachine
  (Layer 1 stays LLM-free); core oracle.ask:15.0 timeout (NL-12a). Reuses
  core.envelope + core.errors only (D1=c). 55 unit + 14 integration (3 real-Ollama,
  -m ollama). ruff + mypy --strict clean. ORACLE fully done (Mode A + Mode B +
  explainability + time-machine L1+L2). — NL-ask GREEN (`2feaf67`)
- ECHO, PULSE, VAULT, TETHER, PURGE — pending (specs in docs/modules/)

**Privileged shim (`chimera/shim/`) — trust-plane, NOT one of the 8 organs:**
- Top-level `chimera/shim/` (§8.8 / §7.10) — a root LaunchDaemon doing EXACTLY 4
  ops, distinct from the 8 module organs AND from the Python `core/`. C17 (Make +
  vendored Unity/cJSON; jsonrpc copied from the CHAFF/MIRROR lineage). Slice 1
  NO-OP security skeleton: socket SERVER (socket/bind/listen/accept — the inverse
  of the CHAFF/MIRROR clients) + real `getsockopt(SOL_LOCAL, LOCAL_PEERCRED)` →
  xucred uid check (deny-by-default; SS-7 resolver-swap seam lets tests inject a
  mock) + 4-op whitelist (lock/evict/reboot/killall — ALL no-op, F3) + auth-first
  JSON-RPC dispatch (ping/pong, §6 error codes -31007/-31002, shim.* namespace).
  23 Unity, binary -Werror clean. peercred-only (SS-6 — NO per-boot secret this
  slice). `ownership_apply` (SS-0(b) chmod 0660 + chown root:operatorgroup) =
  documented-stub, applied only under the manual `-m privileged` tier (not
  hermetic, SS-7). — Slice 1 GREEN (`e60e8ae`)

`chimera/proto/` — still empty (`.gitkeep`).

**Tooling:** `pyproject.toml` + `uv.lock` + `.venv` (Python 3.13.9); ruff + mypy (strict) + pytest configured. Direct deps: cryptography, pydantic(-settings), **ollama==0.6.2** (§6-allowed; httpx + anyio/certifi transitive). pytest markers: `integration`, `ollama`.

**Tests:**
- Python (pytest, default): 438 passing (31 errors + 41 envelope + 36 config + 35 tokens + 36 broker + 63 lifecycle + 60 registry + 81 server + 12 oracle observe-first + 17 oracle Mode B + 10 oracle explainability + 8 oracle time-machine + 8 oracle NL-ask [7 ask + 1 advisory])
- Python (integration, marked — `pytest -m integration`): 22 passing (4 CHAFF + 4 MIRROR + 14 ORACLE: 4 observe-first + 3 Mode B hermetic + 2 Time-Machine query + 2 NL-ask + 3 real-Ollama); the 3 real-Ollama skip when Ollama is down
- Python (ollama, marked — `pytest -m ollama`): 3 passing (subset of integration; real llama3.2:1b)
- Native (CHAFF Unity): 46 passing (7 endpoints + 6 schedule + 6 crypto + 6 db + 10 jsonrpc + 6 commands + 5 generation)
- Native (MIRROR Unity): 42 passing (6 perturb + 6 profile + 5 exclude + 5 stats + 4 rng + 10 jsonrpc + 6 commands)
- Native (shim Unity): 23 passing (11 ops + 6 peercred + 2 server + 4 protocol) — separate C trust-plane suite, NOT in pytest
- Total: 571 passing (548 + 23 shim Unity; ollama subset not double-counted)

**Open tails (honest tracking, MANIFESTO §4):**
- Fernet at-rest: CHAFF (C/OpenSSL) and ORACLE (Python `cryptography.Fernet`) share the format but interop is NOT cross-tested (B1 deferred; format-faithful).
- No supervisor — CHAFF, MIRROR, and ORACLE all exit on core-disconnect (graceful, no module auto-restart yet). Core auto-restart is launchd's job (a LaunchAgent KeepAlive plist), which is SEPARATE from the §8.8 privileged-ops shim — §7.10 prose conflates the two.
- Privileged shim (§8.8) — Slice 1 NO-OP skeleton DONE (`e60e8ae`): socket SERVER + peercred (LOCAL_PEERCRED) + 4-op enum + ping/pong; peercred-only (SS-6, no secret); all 4 ops no-op (F3 — ZERO destructive effect). Scope is EXACTLY 4 root ops: lock screen (TETHER L1), evict CHIMERA Keychain (PURGE Tier 0), force-reboot (PURGE post-action), force-killall (Core §7.7 shutdown). §8.8 explicitly never opens sockets, reads files, or runs operator code; only core talks to it (per-boot shared secret — Slice 2).
- Shim Slice 2 (per-boot secret handshake) — gated on code-signing (§5.5 / Finding F2): the in-memory secret only beats a same-uid attacker once core's memory is hardened-runtime-protected. SAME code-signing tail that gates the MIRROR CGEventTap.
- Shim `ownership_apply` (SS-0(b): chmod 0660 + chown root:operatorgroup) = documented-stub — real chmod/chown is a `-m privileged`-tier follow-up (not hermetically testable, SS-7; non-root skeleton binds at umask default).
- Shim real ops (lock/evict/reboot/killall) = Slice 3+ — landed one at a time, destructive (evict/reboot) LAST and only behind the Slice 2 secret; reboot never in autotests (SH-11).
- Packet-plane root is a SEPARATE track, NOT the §8.8 shim: CHAFF Phase A (pf/dtrace) and ECHO (pfctl/BPF/raw socket) need packet-level root, which §8.8 forbids — future §8 amendment or a dedicated packet-helper. CHAFF code returns required_capability='privileged_shim' for profile.*, but §8.8 grants no such capability — spec gap to resolve before that path unblocks.
- VAULT's blocker is Keychain / Secure-Enclave entitlements (code-signing + TCC), not root — the §8.8 shim does not unblock VAULT (it evicts Keychain for PURGE, it does not grant access).
- 5 of 8 native modules pending (ECHO, PULSE, VAULT, TETHER, PURGE) — CHAFF + MIRROR + ORACLE done.
- MIRROR CGEventTap install — GATED on code-signing + Accessibility TCC (§6/§9); mirror.enable returns -31004 until then.
- MIRROR no event producer yet — daemon wiring done, but drain_events is only a forward-compat seam (queue empty); events ship when the tap lands.
- MIRROR → PULSE aggregate-event gap (D8) — PULSE expects a periodic aggregate event MIRROR doesn't yet define; address at PULSE time.
- ipc/jsonrpc duplicated chaff ↔ mirror (D1=C — extract to modules/common/ at the next *C* native module; ORACLE is Python, so it did not trigger it).
- ORACLE classify is baseline-aware and explainable: returns {score, reasoning, context_factors[], similar_events[]}; advisory-only — returns data, never acts/emits.
- ORACLE classifications_today is in-memory and approximate (no day-rollover).
- ORACLE mid-call Ollama death surfaces as a generic error, not -31004 (startup probe + per-ConnectionError catch cover the typical down cases).
- ORACLE similar_events is naive recency (top-3 same source+type) — embeddings-based similarity is v2 (TODO).
- ORACLE explainability deferred: oracle.explain (separate method) + confidence field (EP-2 enriched classify instead).
- ORACLE next slices: auto-classify per event + oracle.anomaly.detected emission + oracle.model.swap (similar_events debt already repaid naive).
- ORACLE Time-Machine Layer 2 (NL ask) DONE — oracle.ask: enum-intent → Layer 1 dispatch → code-templated answer; "unknown" fallback.
- ORACLE NL-ask: enum stops invented queries but NOT semantic mis-routing (1B answered "whatsapp" to a "chaff" question); raw_result is the transparent safeguard.
- ORACLE Layer 2 LLM-narration deferred (code-template now; richer narration + timeout re-check next); trend/compare/new_since routing deferred.
- ORACLE first core touch: core/server.py METHOD_TIMEOUTS += oracle.ask:15.0 (NL-12a, data-driven cold ~4.4s).
- ORACLE baseline.export (§5.3 spec-debt) explicitly deferred (TM-9b) — separate slice.
- ORACLE real event input is CHAFF only — MIRROR emits nothing yet, so chaff.* is the sole live source feeding the baseline.
- ORACLE standalone `python -m oracle` needs modules/oracle on PYTHONPATH (proper editable-package install is a follow-up; __main__ cannot self-fix the import path).
- ORACLE client.py (D1=c, Python) carries a TODO to extract a shared Python module-client at the 2nd Python module (mirror of the C D1=C duplication).
