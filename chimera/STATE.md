# CHIMERA — Project State Snapshot

> Updated: 2026-06-06
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
shim (trust-plane, NOT an organ): Slice 1 NO-OP skeleton (RED→GREEN) done. TETHER
(native module, §5.7): Slice 1 engine (RED→GREEN) + daemon-wiring (RED→GREEN) +
Slice 3A react-entrypoint (RED→GREEN) done. CORE: idea #3 Slice 3B anomaly-relay
(RED→GREEN) done — a NEW core capability. ORACLE: idea #3 Slice 3C anomaly-emit
(RED→GREEN) done — the real producer.
Last completed: **ORACLE anomaly-emit — Slice 3C** (commit `ee794ba`) — idea #3
(Anomaly-Tripwire), the real producer for the 3B relay (it had run on a synthetic
event). `_handle_classify`: after `detector.classify`, when `result["score"] >=
detector.get_threshold()` (baseline_meta, default 0.7), ADDITIONALLY emit a
Notification `oracle.anomaly.detected` with the advisory payload {score, threshold,
source, type, reasoning}. The emit lives in the CLIENT, never the detector — the
detector stays advisory-pure (D4), so Mode B 17 + advisory 3 + observe-first 12 are
untouched; classify's return is unchanged (contract 1:1). `EVENTS` += the topic so
core.register advertises it. ⚠️ advisory boundary EVOLVED (announce ≠ act): ORACLE
now emits an advisory event on a threshold breach but still never ACTS — it cannot
invoke another module (D7 module guard); core (3B) routes the event to
tether.heighten. Consistent with the existing oracle.baseline.updated emit. MVP =
emit-on-classify (operator-triggered); auto-classify-per-event is a later tail.
Hermetic — FakeDetector score + FakeWriter, no Ollama, no sockets (first
client-unit file, test_oracle_client.py, +3). e2e is 3D. 58 oracle unit + 446
default; ruff + mypy clean. (Prior: CORE anomaly-relay 3B `666794d`; TETHER Slice 3A
`994a5c4`; shim Slice 1, `e60e8ae`.)

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
- `server` (§6.3 + §6.2 + §6.9) — Server: two UNIX sockets, core.* dispatch + 4A module routing (internal-id correlation, per-method timeouts, fail-closed), 3B token reissue, event push, graceful shutdown — DONE (`33f2d38`; 4A routing `06bf7cb`). + idea #3 Slice 3B anomaly-relay (`666794d`): `_issue_to_module` (extracted from `_route`, 1:1), `_dispatch_internal` (core-initiated command, in-process authority — NEW; D7 unchanged, not wire-reachable), `_relay_handle`/`_relay_loop` + `RELAY_RULES` ClassVar ({topic→command}); core subscribes itself to the relay topics in a dedicated task (mirrors the sweep task, per-event isolation).

No scaffold remains — all 8 core modules implemented.

**Native modules (`chimera/modules/`) — 4 of 8 started:**
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
  core.envelope + core.errors only (D1=c). 58 unit + 14 integration (3 real-Ollama,
  -m ollama). ruff + mypy --strict clean. ORACLE fully done (Mode A + Mode B +
  explainability + time-machine L1+L2). + idea #3 Slice 3C anomaly-emit (`ee794ba`):
  `_handle_classify` emits `oracle.anomaly.detected` (advisory Notification {score,
  threshold, source, type, reasoning}) when score >= get_threshold() (default 0.7);
  emit in the CLIENT, detector advisory-pure (untouched); EVENTS += the topic;
  contract 1:1; announce ≠ act (core 3B routes). First client-unit file
  (test_oracle_client.py, +3; FakeDetector/FakeWriter, hermetic). — anomaly-emit
  GREEN (`ee794ba`)
- `tether` (§5.7) — fourth native module, the FIRST and only C++17 module (spec
  §4: ObjC++ bridges CoreBluetooth). Slice 1 = pure-logic ENGINE + daemon-wiring +
  Slice 3A react-entrypoint, all done (engine→daemon staged like MIRROR). Engine:
  EWMA smoothing (α=0.3),
  presence FSM (PRESENT/FRINGE/ABSENT, missed/recover tick counting),
  disappearance classify (FADE / CLEAN_DROP benign / INSTANT_DROP suspicious),
  escalation ladder (grace→L1→L2→L3). Daemon: Monitor.step composes the engine
  units (EWMA→FSM→classify→escalation), emits transition events (present/fringe/
  absent+class/recovered/suspicious) + escalation-on-stage-change while absent;
  daemon_run does core.register (tether.* + 6 real events, depends_on=[]) → inline
  poll loop (serve via 4A, TICK→Monitor.step→emit, 10s heartbeat); make_source
  env-gated (TETHER_SYNTHETIC_RSSI→SyntheticSource else CoreBluetoothSource, gated/
  empty — §4 never fabricates presence). Escalation is EMIT-ONLY — engine evaluate()
  / Monitor.step() return descriptors, never act; core enforces L1 (shim) / L2
  (VAULT) / L3 (PURGE) per spec §5. L3 opt-in, default DISABLED; INSTANT_DROP shifts
  the schedule later (anti-weaponization). Slice 3A react-entrypoint (idea #3):
  tether.heighten/relax + effective_grace_ms(base, heightened) with HEIGHTEN_FACTOR=2
  (grace halved → escalation REQUESTED sooner), shared by commands (status/dry-run)
  + Monitor; relax is an exact idempotent restore (base grace_ms never mutated);
  Monitor.set_heightened re-arms the ladder with the effective grace (real sync,
  engine class untouched). EMIT-ONLY holds — more sensitive, never more active.
  3A = grace-only (near_threshold-heighten deferred — PresenceMachine not re-armed).
  BLE source (CoreBluetooth) + clock behind
  seams → hermetic; the real source is GATED (Bluetooth HW + TCC). tether.test =
  dry-run (§8, no action/emit). §6 codes (-31002 unknown, -31004 gated pairing),
  tether.* namespace. 48 C++ Unity (35 engine + 10 commands + 10 monitor; extern "C"
  setUp/tearDown) + 5 integration, binary -Werror clean. cJSON vendored; jsonrpc/ipc
  are fresh C++ but jsonrpc.c remains the 4th copy (TE-7b deliberate debt). GATED/
  pending: CoreBluetooth .mm source (prod empty), IRK/Keychain pairing (= VAULT
  entitlement blocker), real L1/L2/L3 effects (no live consumer until shim ops /
  VAULT / PURGE exist). — Slice 3A heighten/relax GREEN (`994a5c4`)
- ECHO, PULSE, VAULT, PURGE — pending (specs in docs/modules/)

**Idea #3 — Anomaly-Tripwire (ORACLE anomaly → core relay → TETHER react):**

A cross-module wiring: when ORACLE flags an anomaly, core relays it into a TETHER
reaction (tighten the dead-man grace). Path decision = **B (core-relay)**, NOT a
TETHER subscribe — core mediates so TETHER stays ignorant of ORACLE and the star
topology stays clean. (A — TETHER subscribing oracle.anomaly.detected — was
rejected despite the existing ORACLE←chaff.* event-subscription precedent, because
it couples TETHER to ORACLE's topic. The D7 command-plane guard is preserved: only
core, as authority, turns the event into a command.) Slices:
- **3A — TETHER react-entrypoint** — DONE (`994a5c4`): tether.heighten/relax +
  Monitor sync, EMIT-ONLY (sensitivity, not actuation), engine untouched.
- **3B — CORE relay** — DONE (`666794d`): core-internal broker-subscription on
  oracle.anomaly.detected + declarative `RELAY_RULES` {topic→command} +
  `_dispatch_internal` (core issues the command as authority, in-process, no
  caller-id rewrite, D7 unchanged — not wire-reachable); resilient (await-timeout,
  MODULE_OFFLINE if TETHER absent, never crashes the consume loop). `_issue_to_module`
  extracted from `_route` (1:1). Hermetic (synthetic anomaly).
- **3C — ORACLE emit** — DONE (`ee794ba`): `_handle_classify` emits
  oracle.anomaly.detected when score >= threshold (advisory Notification; emit in
  the client, detector untouched). MVP = emit-on-classify; auto-classify-per-event
  = later tail. Hermetic client-unit (no Ollama/sockets).
- **3D — e2e integration** — NEXT: all three links exist (3A+3B+3C) — prove the
  full chain in one test: ORACLE classify (high score) → broker → core relay →
  tether.heighten actually invoked, over real sockets.

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
- Python (pytest, default): 446 passing (31 errors + 41 envelope + 36 config + 35 tokens + 36 broker + 63 lifecycle + 60 registry + 86 server [81 + 5 anomaly-relay 3B] + 12 oracle observe-first + 17 oracle Mode B + 10 oracle explainability + 8 oracle time-machine + 8 oracle NL-ask [7 ask + 1 advisory] + 3 oracle anomaly-emit [3C client-unit])
- Python (integration, marked — `pytest -m integration`): 27 passing (4 CHAFF + 4 MIRROR + 5 TETHER + 14 ORACLE: 4 observe-first + 3 Mode B hermetic + 2 Time-Machine query + 2 NL-ask + 3 real-Ollama); the 3 real-Ollama skip when Ollama is down. NOTE: real-socket integration needs a short `--basetemp` (AF_UNIX path-too-long, see Open tails)
- Python (ollama, marked — `pytest -m ollama`): 3 passing (subset of integration; real llama3.2:1b)
- Native (CHAFF Unity): 46 passing (7 endpoints + 6 schedule + 6 crypto + 6 db + 10 jsonrpc + 6 commands + 5 generation)
- Native (MIRROR Unity): 42 passing (6 perturb + 6 profile + 5 exclude + 5 stats + 4 rng + 10 jsonrpc + 6 commands)
- Native (shim Unity): 23 passing (11 ops + 6 peercred + 2 server + 4 protocol) — separate C trust-plane suite, NOT in pytest
- Native (TETHER C++ Unity): 48 passing (4 ewma + 6 presence + 4 classify + 8 escalation + 6 emit + 10 commands + 10 monitor) — separate C++ suite, NOT in pytest
- Total: 632 passing (446 default + 27 integration + 46 CHAFF + 42 MIRROR + 23 shim + 48 TETHER Unity; ollama subset not double-counted)

**Open tails (honest tracking, MANIFESTO §4):**
- Fernet at-rest: CHAFF (C/OpenSSL) and ORACLE (Python `cryptography.Fernet`) share the format but interop is NOT cross-tested (B1 deferred; format-faithful).
- No supervisor — CHAFF, MIRROR, and ORACLE all exit on core-disconnect (graceful, no module auto-restart yet). Core auto-restart is launchd's job (a LaunchAgent KeepAlive plist), which is SEPARATE from the §8.8 privileged-ops shim — §7.10 prose conflates the two.
- Privileged shim (§8.8) — Slice 1 NO-OP skeleton DONE (`e60e8ae`): socket SERVER + peercred (LOCAL_PEERCRED) + 4-op enum + ping/pong; peercred-only (SS-6, no secret); all 4 ops no-op (F3 — ZERO destructive effect). Scope is EXACTLY 4 root ops: lock screen (TETHER L1), evict CHIMERA Keychain (PURGE Tier 0), force-reboot (PURGE post-action), force-killall (Core §7.7 shutdown). §8.8 explicitly never opens sockets, reads files, or runs operator code; only core talks to it (per-boot shared secret — Slice 2).
- Shim Slice 2 (per-boot secret handshake) — gated on code-signing (§5.5 / Finding F2): the in-memory secret only beats a same-uid attacker once core's memory is hardened-runtime-protected. SAME code-signing tail that gates the MIRROR CGEventTap.
- Shim `ownership_apply` (SS-0(b): chmod 0660 + chown root:operatorgroup) = documented-stub — real chmod/chown is a `-m privileged`-tier follow-up (not hermetically testable, SS-7; non-root skeleton binds at umask default).
- Shim real ops (lock/evict/reboot/killall) = Slice 3+ — landed one at a time, destructive (evict/reboot) LAST and only behind the Slice 2 secret; reboot never in autotests (SH-11).
- TETHER (§5.7) — Slice 1 ENGINE (`7269080`) + daemon-wiring (`c2c0882`) + Slice 3A react-entrypoint (`994a5c4`) all done: connect→register→serve via 4A router + TICK→Monitor.step→emit + heartbeat (staged like MIRROR) + tether.heighten/relax. Monitor.step composes the engine units (EMIT-ONLY, never acts). TE-1…TE-10 decisions live in commit history; no separate design-record yet (a docs/TETHER_DESIGN.md is warranted only if it grows).
- TETHER Slice 3A react-entrypoint (`994a5c4`) — tether.heighten/relax flip a `heightened` flag; effective_grace_ms(base, heightened) applies HEIGHTEN_FACTOR=2 (grace halved → escalation requested sooner), shared by commands + Monitor; relax is an exact idempotent restore (base grace_ms never mutated); Monitor.set_heightened re-arms the ladder with the effective grace (real sync — test_heightened_escalates_sooner proves it, not a flag-only stub). Engine class untouched. EMIT-ONLY: more sensitive, never more active. This is idea #3's TETHER leaf — see the Idea #3 section. 3A = grace-only.
- TETHER escalation is EMIT-ONLY (spec §5) — engine evaluate() / Monitor.step() return a decision; CORE enforces L1→shim.lock, L2→VAULT vault.lock, L3→PURGE purge.trigger. TETHER never locks/evicts/reboots itself. Idea #3 (ORACLE anomaly → TETHER react): Slice 3A (TETHER react-entrypoint) + 3B (CORE relay) + 3C (ORACLE emit) DONE; 3D (e2e) NEXT — all three links exist (ORACLE emits oracle.anomaly.detected → core relays → tether.heighten), NOT a TETHER subscribe (keeps the star topology clean). Path B locked; see the Idea #3 section for the full slice plan.
- CORE-initiated command is a NEW capability (idea #3 3B, `666794d`): before, core only forwarded operator commands via `_route`; now `_dispatch_internal` lets core issue a command to a module on its OWN authority. ⚠️ D7 is preserved — `_dispatch_internal` is in-process only, NOT wire-reachable (no JSON-RPC method maps to it), so a module-over-the-wire invoking another module still gets -31007 (NOT_AUTHORIZED). The relay loop is the only caller; resilient (try/except → log, never crashes the consume loop).
- RELAY_RULES is declarative {event_topic → module.method}, a Server ClassVar (METHOD_TIMEOUTS precedent). One rule now: oracle.anomaly.detected → tether.heighten. Adding a tripwire = adding a row, not code. Param-mapping deferred — v1 issues the command with NO params (tether.heighten needs none); a payload→params mapper lands only when a future rule requires it.
- ⚠️ config.set → Monitor grace-sync gap (PRE-EXISTING, not introduced by 3A): tether.config.set mutates rt.escalation.grace_ms (+ presence.near_threshold), but the Monitor holds its OWN ec_ — only l3_armed is mirrored to the live Monitor (set_l3_armed). So a grace change via config.set does NOT reach the running ladder. Slice 3A heighten DOES its part correctly (set_heightened is mirrored after dispatch, beside the l3 sync); config.set's grace/near_threshold sync is a separate tail to fix (mirror config.set → Monitor too, or have Monitor read live config).
- TETHER near_threshold-heighten deferred — Slice 3A is grace-only (the escalation ladder is re-armed per ABSENT, so an effective grace applies naturally). Heightening near_threshold would need the PresenceMachine (constructed once, NOT re-armed) to read live config or be reconstructed — a later tail if anomaly-reaction should also detect absence sooner.
- TETHER GATED / out of slice: CoreBluetooth .mm BLE source (Bluetooth HW + TCC) — make_source returns an EMPTY gated CoreBluetoothSource in production (no synthetic fallback off TETHER_SYNTHETIC_RSSI — §4 never fabricates presence); IRK/companion pairing in Keychain/Secure Enclave (the SAME entitlement blocker as VAULT); real L1/L2/L3 effects (core-enforced downstream — L2 needs VAULT, L3 needs PURGE, neither built). The escalation L1/L2/L3 events have no live consumer until shim ops / VAULT / PURGE exist.
- 4th jsonrpc copy (chaff→mirror→shim→tether) — TE-7b DELIBERATE debt; a shared `modules/common/` extract is a future slice. TETHER's jsonrpc/ipc are fresh C++ but jsonrpc.c is still the 4th copy of the lineage. The duplication is growing (now 4 copies); revisit before a 5th consumer. TETHER (C++) links the C copy via the header's extern "C".
- AF_UNIX path-too-long (env, NOT code) — real-socket integration (server `TestRealSocket*`, MIRROR, TETHER) binds UNIX sockets under pytest tmp_path; on macOS the default `TMPDIR` (`/var/folders/.../T`, ~48 chars) + pytest dirs + long test names exceeds the ~104-char `AF_UNIX` limit → 18 default `test_server.py` failures + integration breakage. Fix is ENV: `TMPDIR=/tmp/t` for default, `--basetemp=/tmp/tt` for `-m integration`. Confirmed artifact (438 default + 5 TETHER integration green with short paths). Future: a conftest could pin a short socket dir.
- Packet-plane root is a SEPARATE track, NOT the §8.8 shim: CHAFF Phase A (pf/dtrace) and ECHO (pfctl/BPF/raw socket) need packet-level root, which §8.8 forbids — future §8 amendment or a dedicated packet-helper. CHAFF code returns required_capability='privileged_shim' for profile.*, but §8.8 grants no such capability — spec gap to resolve before that path unblocks.
- VAULT's blocker is Keychain / Secure-Enclave entitlements (code-signing + TCC), not root — the §8.8 shim does not unblock VAULT (it evicts Keychain for PURGE, it does not grant access).
- 4 of 8 native modules pending (ECHO, PULSE, VAULT, PURGE) — CHAFF + MIRROR + ORACLE done; TETHER started (engine + daemon-wiring + Slice 3A react-entrypoint done).
- MIRROR CGEventTap install — GATED on code-signing + Accessibility TCC (§6/§9); mirror.enable returns -31004 until then. The code-signing tail is now shared across MIRROR (tap), shim Slice 2 (secret in hardened-runtime memory), and TETHER (CoreBluetooth TCC + IRK in Keychain).
- MIRROR no event producer yet — daemon wiring done, but drain_events is only a forward-compat seam (queue empty); events ship when the tap lands.
- MIRROR → PULSE aggregate-event gap (D8) — PULSE expects a periodic aggregate event MIRROR doesn't yet define; address at PULSE time.
- ipc/jsonrpc duplicated chaff ↔ mirror, and jsonrpc.c also copied into shim + tether (now 4 jsonrpc copies; TE-7b deliberate debt). D1=C extract to modules/common/ deferred to a future slice — see the dedicated 4th-copy tail above.
- ORACLE classify is baseline-aware and explainable: returns {score, reasoning, context_factors[], similar_events[]}; advisory — ⚠️ boundary EVOLVED at 3C (`ee794ba`): classify now ANNOUNCES an advisory event (oracle.anomaly.detected) on a threshold breach (score >= get_threshold()), but still never ACTS (announce ≠ act). ORACLE cannot invoke another module (D7); core (3B) routes the event to tether.heighten. Consistent with the pre-existing oracle.baseline.updated emit. The emit lives in the client (_handle_classify), so the detector stays advisory-pure (returns data, mutates nothing — test_oracle_advisory still holds).
- ORACLE classifications_today is in-memory and approximate (no day-rollover).
- ORACLE mid-call Ollama death surfaces as a generic error, not -31004 (startup probe + per-ConnectionError catch cover the typical down cases).
- ORACLE similar_events is naive recency (top-3 same source+type) — embeddings-based similarity is v2 (TODO).
- ORACLE explainability deferred: oracle.explain (separate method) + confidence field (EP-2 enriched classify instead).
- ORACLE next slices: oracle.anomaly.detected emission DONE (3C, emit-on-classify MVP); remaining — auto-classify-per-event (Observer classifies each observed event via the LLM and emits without an operator call — deferred: an LLM call per event is expensive + D6 Ollama-gated) + oracle.model.swap (similar_events debt already repaid naive).
- ORACLE 3C emit-on-classify is operator-triggered (fires only on an oracle.classify call). The Mode A learning path (Observer) does NOT auto-classify — so no anomaly events flow without an operator invoking classify yet; auto-classify-per-event is the tail that makes the tripwire autonomous.
- First ORACLE client-unit file (test_oracle_client.py, 3C) — exercises the emit-side (`_handle_classify`) hermetically via FakeDetector (fixed score, no Ollama) + FakeWriter (captures frames, no socket). Distinct from the 0.42 FakeDetector in test_oracle_integration. Earlier client behaviour was only covered via integration (real sockets); this is the first hermetic client-level unit.
- ORACLE Time-Machine Layer 2 (NL ask) DONE — oracle.ask: enum-intent → Layer 1 dispatch → code-templated answer; "unknown" fallback.
- ORACLE NL-ask: enum stops invented queries but NOT semantic mis-routing (1B answered "whatsapp" to a "chaff" question); raw_result is the transparent safeguard.
- ORACLE Layer 2 LLM-narration deferred (code-template now; richer narration + timeout re-check next); trend/compare/new_since routing deferred.
- ORACLE first core touch: core/server.py METHOD_TIMEOUTS += oracle.ask:15.0 (NL-12a, data-driven cold ~4.4s).
- ORACLE baseline.export (§5.3 spec-debt) explicitly deferred (TM-9b) — separate slice.
- ORACLE real event input is CHAFF only — MIRROR emits nothing yet, so chaff.* is the sole live source feeding the baseline.
- ORACLE standalone `python -m oracle` needs modules/oracle on PYTHONPATH (proper editable-package install is a follow-up; __main__ cannot self-fix the import path).
- ORACLE client.py (D1=c, Python) carries a TODO to extract a shared Python module-client at the 2nd Python module (mirror of the C D1=C duplication).
