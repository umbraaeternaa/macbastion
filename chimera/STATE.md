# CHIMERA — Project State Snapshot

> Updated: 2026-06-08
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
(RED→GREEN) done — the real producer. **Idea #3 (Anomaly-Tripwire) COMPLETE** —
3A+3B+3C wired + e2e-confirmed by 3D.
Last completed: **PURGE target registry** (commit `aea7b86`) — §3/§7, PR-1…5. The operator's
Tier-2 destruction list: `targets.{h,c}` — a bounded (64) in-memory `purge_targets_t` of
{path, encrypted} with `purge_target_add` (idempotent by path; rejects NULL/empty/too-long/full
with -1), `purge_target_remove` (idempotent), count/at accessors, and `purge_plan_targets()`
bridging the registry into the dry-run plan (encrypted -> shred, unencrypted -> skip). 9 Unity
RED->GREEN (16/16 PURGE total). ⚠️ DEFERRED: persistence (~/.config/chimera/purge/) + IPC
purge.target.* (daemon) + gated encryption detection (encrypted flag operator-supplied for now).

Prior milestone: **PURGE dry-run planner** (commit `1481d6d`) — §5.8 §4/§8, PG-1…5. The 8TH and
FINAL organ starts — **all 8 modules now underway**. A NEW C module (`modules/purge/`, mirrors
CHAFF/ECHO). First slice = the `purge.test` dry-run + the §8 honest-wipe rule, and it DESTROYS
NOTHING: `purge_classify(encrypted)` → SHRED if encrypted, else SKIP_UNENCRYPTED (PURGE refuses
to pretend-wipe unencrypted SSD — no security theatre); `purge_build_plan(...)` builds the
keys-first tier report (Tier 0 + Tier 3 always-on, Tier 1 configurable, Tier 2 classified only
when enabled). 7 Unity RED->GREEN; added to check.sh. ⚠️ DEFERRED/GATED: ALL real destruction —
Keychain eviction, Mach VM, ARM64 dc zva, libsodium/explicit_bzero, the daemon + purge.arm/trigger
+ emergency choreography.

Prior milestone: **ECHO stats core** (commit `a0a8014`) — §5.2 §5, ET-1…5. ECHO's accounting:
`stats.{h,c}` — `echo_stats_t` accumulates per-tick (real, padding) into totals + a 10-bin decile
histogram of per-tick padding ratio (idle ticks land in the top bin, active in the bottom —
disambiguates §5's vague "histogram"). `echo_padding_ratio_pct` = overall padding share (0 if
empty, no div-by-zero); `echo_padding_surge(threshold)` = the §5 echo.padding.surge trigger
(ratio >= 80%). 7 Unity RED->GREEN (23/23 ECHO total). With this ECHO's pure LOGIC is complete
(shaper + config + stats). ⚠️ DEFERRED: windowed 1m/1h/1d query (needs a timestamped ring
buffer) + IPC echo.stats + echo.padding.surge emission (all daemon).

Prior milestone: **ECHO config core** (commit `2f381ce`) — §5.2 §3, EC-1…5. The operator knobs
for ECHO: `config.{h,c}` — `echo_config_t {target_kbps, burst_tolerance}` + `echo_config_default()`
= {100, 200} (§3) + `echo_config_valid()` (range bounds) + `echo_config_set(cfg, *target, *burst)`
— a partial update (NULL = unchanged) that validates ALL provided fields and rejects ATOMICALLY
(cfg untouched on a bad value) + `echo_config_budget(cfg, tick_ms)` bridging config -> the shaper.
7 Unity RED->GREEN (16/16 ECHO total). ⚠️ DEFERRED: IPC echo.config.set/get (needs the ECHO
daemon, not built) + persistence to ~/.config/chimera/echo/.

Prior milestone: **ECHO shaper core** (commit `ca06b25`) — §5.2 §3, ES-1…6. A NEW C module
(`modules/echo/`, mirrors CHAFF's scaffold — strict-c17 Makefile + Unity), the bandwidth-
normalizer pair to CHAFF. First hermetic slice = the pure constant-rate-padding math:
`echo_budget_bytes(target_kbps, tick_ms)` (100KB/s @10ms = 1024 B/tick) + `echo_shape(queued,
budget, burst) -> {real_send, padding}` = min(queued, budget+burst) real + max(0, budget-real)
padding, so the WIRE stays FLAT at budget whenever queued <= budget (the hiding guarantee —
idle and light traffic look identical on the wire), bursting to budget+burst to drain a backlog.
9 Unity RED->GREEN; added to check.sh. ⚠️ DEFERRED/GATED: pf/BPF packet I/O + raw sockets +
padding emission (root/kernel, like MIRROR's tap) + config/stats DB + IPC/jsonrpc daemon (echo.*).

Prior milestone: **PULSE §6 finishers — calibrate + pulse.error** (commit `53547ad`) — PF-1…7,
closing PULSE's §6 method surface. Store (`baseline.py`): `calibration_days(now)` = distinct days
in the window (baseline_ready now reuses it, DRY) + `clear()` wipes all buckets. Daemon
(`client.py`): `pulse.calibrate.start` reports {days_observed, days_required:14, ready, started_at}
and stamps the calibration epoch (idempotent); `pulse.calibrate.reset` clears the store to
recalibrate (operator-invoked). `_safe_tick` wraps the tick loop — on ANY error it emits
`pulse.error {where, message}` and continues (fail-open §8), making the registered-but-silent
pulse.error event a real producer. 5 unit RED->GREEN; ruff + mypy --strict clean. 788 -> 793 (+5).
PULSE's §6 surface is now COMPLETE; only its live signal inputs remain gated.

Prior milestone: **core.override.set** (commit `22aebc7`) — operator set-phrase path, OS-1…4.
A new core method lets the OPERATOR set/change the gate-override phrase: `_handle_override_set`
is surface-only (a module connection — even with a valid core token — is refused -31007; the
phrase is the operator's, never a module's), needs a configured OverrideStore (-31004) and a
non-empty phrase (-32602), then calls set_phrase. 5 unit RED->GREEN (via handle_command with a
surface/module Connection); ruff + mypy --strict clean. 783 -> 788 (+5). The whole gate+override
chain is now operator-controllable end to end. ⚠️ DEFERRED: change-requires-old-phrase hardening,
confirm-dialog (surface), external-OS gating.

Prior milestone: **override-phrase store** (commit `3564968`) — §8 autonomy escape, OV-1…6.
`core/override.py` `OverrideStore`: a salted PBKDF2-SHA256 hash of the operator's override
phrase (random 16-byte salt, 200k iterations) persisted as JSON at override.json (0600) — the
phrase is NEVER stored in the clear; verify() is constant-time (`hmac.compare_digest`) and False
when unset. Wired into the gate (OV-3): `_gate(method, params)` reads an `_override` phrase from
the request, verifies it, and passes override_ok to decide() — so an exhausted block is escapable
with the right phrase (§8: a speed bump, not a cage). `_route` STRIPS `_override` before
forwarding — the secret never reaches the module. 7 store-unit + 3 gate-wiring (override allows /
wrong blocks / strip) RED->GREEN; ruff + mypy --strict clean. 773 -> 783 (+10). ⚠️ DEFERRED: the
operator path to SET the phrase (a `core.override.set` method / CLI — set programmatically for
now) + confirm-dialog (surface) + external-OS gating.

Prior milestone: **core gate live-wiring** (commit `fbe64cc`) — GW-1…6, the gate now ACTS.
`core/server.py` enforces the §4 decision on the live command path: `_route` calls
`_gate(method)` before forwarding — a danger CHIMERA-command is BLOCKED at exhausted
(`-31003 DENIED_BY_POLICY`) or DELAYED at tired (asyncio.sleep), else forwarded. Core tracks
PULSE's mode (subscribes to `pulse.mode.changed`, GW-2) and refreshes the cached danger set
from `pulse.danger.list` when PULSE registers (GW-3, core-authority query). fail-OPEN
throughout: an unknown mode / refresh failure never blocks. 5 unit + 2 integration RED->GREEN
(integration 10.5s timeouts -> 0.24s — the wiring signal); ruff + mypy --strict clean. 766 ->
773 (+7). ⚠️ DEFERRED: confirm-dialog + override-phrase entry (need the surface — core can't
prompt mid-route), salted-hash override storage, gating of external OS actions (rm/git never
flow through core — need a CLI/shell gate), live danger-set refresh on registry change (only on
PULSE register now). override_ok is always False this slice.

Prior milestone: **core cognitive gate (decision)** (commit `7d6c8fa`) — §4 friction + §8
autonomy invariant, GE-1…5. `core/gate.py` `decide(action, mode, danger, *, override_ok)` ->
GateDecision: a danger action gets friction by PULSE's mode — normal→allow, caution→confirm,
tired→delay(5s), exhausted→block (a correct override escapes). Non-danger actions always allow.
fail-OPEN (§8): an unknown/None mode NEVER blocks — a broken cognitive sensor must not lock the
operator out (opposite of VAULT's fail-closed). The override phrase is a speed bump, never a
cage. Pure (no I/O), 8 unit RED->GREEN; ruff + mypy --strict clean. 758 -> 766 (+8). This is the
CONSUMER PULSE was missing — but only the DECISION heart; ⚠️ the live wiring (core tracks
pulse.mode.changed + caches the danger registry + hook in `_route` + real confirm/delay/block +
salted-hash override storage) is the next slice.

Prior milestone: **PULSE danger-registry** (commit `b87be5a`) — §5.5 §4/§6/§7, DR-1…6. The
operator-editable registry of danger-action signatures: `registry.py` `DangerRegistry` = plain
JSON at registry.json (NOT encrypted — operator config, not raw data; dir 0700 / file 0600),
seeds the §4 defaults on first use, add/remove idempotent. Wired into the daemon:
`pulse.danger.add/remove/list` via the 4A router (DangerRegistry injected; -31004 if absent),
each returns {registry:[...]}. 5 unit + 2 integration RED->GREEN; ruff + mypy --strict clean
(mypy caught a `list`-method-shadows-builtin + an Any-return — both fixed). 751 -> 758 (+7).
⚠️ DEFERRED: the CONSUMER — core gate-enforcement that reads the registry to gate actions — is
not built; the registry is the operator's editable list, no live gating yet.

Prior milestone: **PULSE mode.changed emission** (commit `76e9955`) — §5.5, EM-1…6. The daemon
now EMITS `pulse.mode.changed` on a mode transition: a tick-loop computes `_compute(now)`
(temporal_signal -> assess; primary_signal='temporal' — the only present group this slice), and
on a real mode change emits {old_mode, new_mode, score, primary_signal} as an advisory
Notification (announce ≠ act; core relays per §5). The first tick establishes _last_mode (no
emit). 3 hermetic client-unit RED->GREEN (FakeWriter + seeded store + injected now); ruff + mypy
--strict clean. 748 -> 751 (+3). ⚠️ emission is DORMANT during calibration (baseline_ready False
-> mode always 'normal' -> no transitions); it fires once calibrated / with live signals.
pulse.error not yet emitted.

Prior milestone: **PULSE daemon** (commit `44280d2`) — §5.5, PULSE becomes a LIVE module.
`client.py` (module-only, mirrors ORACLE's command connection): opens core.sock, core.register
(pulse.* + 2 events, depends_on=[]), serves pulse.* via the 4A router, heartbeats. `pulse.status`
composes the live edge — temporal_signal(now) feeds the empty `temporal` slot of assess(store,…)
-> {score, mode, baseline_ready, session_minutes}; advisory + fail-OPEN (uncalibrated -> mode
'normal', §8). pulse.weights.set (sum=1.0 validated) / enable / disable. `__main__.py` = `python -m
pulse` (CoreConfig + BaselineStore + signal-cancelled asyncio.run). 4 integration RED->GREEN
(wall-clock 20.75s timeouts -> 0.45s registered — the wiring signal); ruff + mypy --strict clean.
744 -> 748 (+4 integration). ⚠️ DEFERRED: events emission (mode.changed producer), calibrate/
danger/override subsystems, live signal collection (MIRROR group-A consumer, kqueue idle, ORACLE
drift), core gate-enforcement.

Prior milestone: **PULSE temporal — group B** (commit `abd2bf3`) — §5.5, the time-context
fatigue signal that fills the empty `temporal` slot in `assess`. `temporal.py` (pure,
hermetic) maps injected ISO times to one value in [0,1]: a chronotype-weighted hour-of-day
curve (peak ~3am, low midday; night_owl x0.4 on night hours) weighted 0.5 + hours-since-idle/6
clamped 0.25 + session-hours/12 clamped 0.25, all clamped [0,1]. now/session_start/last_idle_end
injected (no clock inside); a missing input contributes 0 (fail-OPEN §8, never inflates).
Chronotype is an input (auto-detect §9 deferred). 10 tests RED->GREEN; ruff + mypy --strict
clean. 734 -> 744 (+10). ⚠️ group-B SCORING done (hermetic); the LIVE collector (kqueue
idle-detection + real clock/session) is still gated.

Prior milestone: **PULSE slice 3 — assess wiring** (commit `54b2751`) — §5.5, the bridge
that connects PULSE's two halves. `assess.py` pulls each present group-A signal's 14-day
baseline from the store, normalizes the current reading via `normalize_delta` (fatigue
direction per GROUP_A_DIRECTIONS), means the present sub-deltas into ONE `input_delta`
(WS-3), builds `Signals`, and calls `score_and_mode` with
`baseline_ready=store.baseline_ready(now)` -> `(score, mode)`. Group-A contract (WS-2, the
PULSE side of gap D8, per §3): typing_speed (slower=fatigue), error_rate + mouse_ineff
(higher=fatigue); the VALUES are caller-supplied so assess stays decoupled from MIRROR's
wire format. temporal (B) + drift (C) caller-supplied this slice (their producers —
kqueue, ORACLE — deferred). Fail-safe inherited from score_and_mode (broken/all-absent ->
`normal`). 10 tests RED->GREEN; ruff + mypy --strict clean. 724 -> 734 (+10).

Prior milestone: **PULSE slice 2 — baseline store** (commit `bef89a6`) — §5.5, the
encrypted history store that feeds the scoring engine its two missing inputs. Mirrors
ORACLE's baseline.py: SQLite + cryptography.Fernet (key 0600 beside DB, dir 0700, db
0600, check_same_thread=False + RLock). Schema (BS-4): `buckets(id, ts plaintext, gated
plaintext, signals_json BLOB Fernet)` + idx + baseline_meta — ts/gated plaintext so SQL
windows + excludes BEFORE decrypt; aggregate signal VALUES Fernet-encrypted at rest (§5;
§8 — aggregates, never raw input). `baseline(key, now)` = 14-day rolling MEDIAN over
NON-gated buckets in half-open `[now-14d, now)`, None if none (BS-5);
`baseline_ready(now)` = >=14 distinct days in window (the 14-day cold-start gate, BS-8);
`purge(now)` drops buckets older than now-14d (BS-7). `signals` is an open {name:float}
dict (BS-9) — no MIRROR field names hardcoded (MIRROR->PULSE aggregate event undefined,
gap D8); `now` always injected as an ISO string (hermetic, deterministic). ⚠️ spec
amended FIRST (`2da2132`, BS-1): PULSE.md retention 7->14d — a 7-day store cannot feed a
14-day median (retention must be >= the median window). 24 tests RED->GREEN; ruff + mypy
--strict clean. ⚠️ STARTED, NOT complete — the store is hermetic; live producers (MIRROR
group-A, ORACLE drift, kqueue idle), the daemon/IPC, and core gate-enforcement remain
DEFERRED. 700 -> 724 (+24).

Prior milestone: **PULSE slice 1 — scoring engine** (commit `d9b0a42`) — §5.5
Cognitive Load Monitor, CHIMERA's first cognitive-state defense and the only module
that watches the OPERATOR, not the system/world. First hermetic slice: a pure-Python
scoring engine (mirrors ORACLE's form). Takes already-normalized signals + a baseline
snapshot -> `(fatigue_score, mode)`: weighted sum of present groups, weights
renormalized to sum 1.0 (§7), score clamped [0,1], mode by §4 thresholds half-open
`[lo,hi)`. ⚠️ **fail-safe = mode `normal`** — a missing/NaN/inf signal or all-absent
tick degrades to LESS friction, NEVER block (autonomy invariant §8, the OPPOSITE of
VAULT's fail-closed). Advisory: emits `(score, mode)`; core enforces gates. 22 tests
RED->GREEN; ruff + mypy --strict clean. ⚠️ slice 1 ONLY (the scoring math) — everything
else DEFERRED (see PULSE structure + open tails). 678 -> 700 (+22).

Prior milestone: **jsonrpc extract to `modules/common/` — JE-1 done** (4 native
modules migrated to one canonical shared unit: chaff `24cf41f` pilot, mirror
`611c16c`, shim `c25dfec`, tether `2245f09`). The four byte-identical (modulo
namespace) per-module jsonrpc copies collapse into `modules/common/{jsonrpc.h,
jsonrpc.c}` with a canonical `jsonrpc_result_t {OK=0, ERR=-1, ERR_PARSE=-2}` and an
`extern "C"` guard (front-loaded in the pilot for the C++ tether link). Each
migration proven behaviour-preserving: a formal normalized-diff = only the one-line
top comment, 0 difference in function bodies, + the module's suite green. C++ tether
verified at link too (common compiled as C via `clang -std=c17`, linked by clang++,
0 undefined symbols — extern "C" holds). TE-7b debt paid, before a 5th copy (VAULT).
678 baseline UNCHANGED (move+rename, 0 new tests). Each native suite re-verified:
chaff 46, mirror 42, shim 23, tether 48, vault 44.

Prior milestone: **VAULT crypto engine** (commit `e82f69b`) — the FIFTH native
module gets real cryptography via libsodium (the first VAULT external dependency;
the pure-C phase ends here, deliberately). Three primitives:
- `vault_crypto_derive` — Argon2id MODERATE (crypto_pwhash, OPSLIMIT/MEMLIMIT_MODERATE,
  ALG_ARGON2ID13); password = master_secret ‖ policy_hash (binds the key to the
  policy). The combined buffer holds the RAW master secret → it lives in sodium_malloc
  secure memory and is sodium_free'd (zeroed) the instant derivation ends; the raw
  secret never reaches swap or a core dump (VAULT's no-leak thesis). Deterministic
  for fixed inputs (stable salt → same key).
- `vault_crypto_seal` / `open` — XChaCha20-Poly1305 with a fresh random 192-bit nonce
  per seal (nonce-misuse-resistant). open verifies the Poly1305 tag BEFORE releasing
  plaintext; on wrong-key/tamper it returns false AND sodium_memzero's pt_out
  (defensive active wipe — fail-closed, no partial leak).
- `vault_secure_alloc/free` — sodium_malloc/free (guard pages + canary + mlock,
  zeroed on free). `_Static_assert`s confirm the size #defines equal libsodium's.
⚠️ **catch 1 RESOLVED:** libsodium chosen; CLAUDE.md §6 amended (`a038979`) to a
per-module allowlist (the old "libcurl only" was already false — CHAFF links
openssl@3+sqlite3). ⚠️ **spec amended (`a038979`):** XChaCha20-Poly1305 replaces
AES-256-GCM (nonce-misuse-resistance, catch B), and key_salt is STABLE not
"per-unlock" (catch A — a per-unlock salt would make stored ciphertext
undecryptable). 44 C Unity (37 engine + 7 crypto); `make all` -Werror clean. (Prior:
VAULT DEFER `165a1de`; slice 1 `655f183`; Anomaly-Tripwire 3D `37c3371`.)

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
- `vault` (§5.6) — FIFTH native module, C17 (joins the CHAFF/MIRROR C lineage; not
  Python/C++). State-gated encrypted storage: the decryption key materializes only
  when an operator-authored policy evaluates ALLOW against the current context (time
  / presence / module-state) — not key-gated (§2). Slice 1 = the PURE policy DSL
  engine: lexer (idents/numbers/"strings"/operators/punct) + recursive-descent
  parser (or>and>not>primary → AST: allow_when expression + optional relock_after)
  + typed evaluator (numeric < <= > >= == != between; enum/string == != in;
  and/or/not/parens). ⚠️ fail-closed tri-state {TRUE,FALSE,ERROR}: NULL policy /
  unknown variable / type mismatch / not-running-module value (no explicit `unknown`
  opt-out) → ERROR, propagates through not/and/or, NEVER → ALLOW; not-TRUE = DENY
  (the security heart, §4). Verdict is the FULL three-way ALLOW/DENY/DEFER:
  `vault_decide` adds temporal projection (`165a1de`) — base FALSE → brute-force
  step a context copy forward (advance_hour 1h, DEFER_CAP_STEPS=168 / 7 days) to the
  first ALLOW → {DEFER, step×3600}; non-time vars frozen so a block time can't lift
  → DENY; ERROR never projected. `vault_eval` stays the instantaneous ALLOW/DENY
  (slice-1 contract intact, no test-fit). 1h resolution (day_of_month/boot-second =
  tail). relock_after parsed (min×60/hour×3600), not scheduled.
  CRYPTO (`e82f69b`, libsodium — first VAULT external dep, pure-C phase ends): Argon2id
  MODERATE derive (password = master_secret‖policy_hash, secure-mem + immediate wipe),
  XChaCha20-Poly1305 seal/open (192-bit random nonce, fail-closed verify+wipe), sodium
  secure memory (guard+canary+mlock). catch 1 RESOLVED (libsodium; §6 amended). Spec
  amended: XChaCha20 over AES-GCM (catch B) + stable key_salt (catch A).
  44 C Unity (6 lexer + 6 parser + 9 evaluator + 6 fail_closed + 3 relock + 7 decide
  + 7 crypto), `make all` -Werror clean. GATED/deferred: Keychain/Secure-Enclave
  master secret (entitlements), mount_tmpfs (catch 2 — root), kqueue relock, IPC/daemon
  (catch 3 — jsonrpc). vault.lock (§6) is the TETHER L2 escalation target.
  — slice 1 `655f183` + DEFER `165a1de` + crypto `e82f69b`
- `common` (`modules/common/`) — NOT an organ: the SHARED jsonrpc unit (JE-1
  extract). `jsonrpc.{h,c}` + `.gitignore`; canonical `jsonrpc_result_t {OK=0,
  ERR=-1, ERR_PARSE=-2}`, `extern "C"` guard. All 4 native consumers
  (chaff/mirror/shim/tether) link it, compiled per-consumer with that module's
  STRICT flags (cJSON-agnostic — the consumer's -I supplies cJSON). VAULT daemon =
  next (first NEW) consumer. — JE-1 done (24cf41f/611c16c/c25dfec/2245f09)
- `pulse` (`modules/pulse/`) — STARTED (NOT complete): scoring slice 1 (`d9b0a42`) + baseline store slice 2 (`bef89a6`)
  + assess wiring slice 3 (`54b2751`) + temporal group B (`abd2bf3`) + daemon (`44280d2`) + mode.changed emission (`76e9955`) + danger-registry (`b87be5a`) + §6 finishers calibrate/pulse.error (`53547ad`). §5.5 Cognitive Load Monitor — the operator-facing cognitive gate
  ("idea #4"), the only module watching the OPERATOR not the system. pure-Python
  (like ORACLE): `scoring.py` weighted-sum + renorm-to-1.0 + mode `[lo,hi)` + clamp +
  delta-normalize; weights validated (Σ=1.0 else ValueError). ⚠️ fail-safe -> `normal`
  (NEVER block; autonomy §8, opposite of VAULT). Advisory: emits `(score, mode)`; core
  enforces gates. `baseline.py` (slice 2) = encrypted SQLite+Fernet store mirroring
  oracle/baseline.py: per-minute aggregate buckets, 14-day rolling-median over non-gated
  buckets in `[now-14d, now)`, baseline_ready (>=14 distinct days), retention purge;
  signals an open {name:float} dict (no MIRROR fields hardcoded — D8); spec amended first
  (BS-1: retention 7->14d). `assess.py` (slice 3, `54b2751`) bridges store->scoring (group-A baseline-normalize ->
  mean input_delta -> score_and_mode, WS-1..7). `temporal.py` (group B, `abd2bf3`) gives the
  temporal slot its value. 22 + 24 + 10 + 10 = 66 Python unit, all RED->GREEN. DEFERRED (later
  slices): MIRROR
  delta-collection (group A live aggregates),
  ORACLE drift (group C), kqueue idle (group B), IPC/daemon, core gate-enforcement +
  danger-registry + override-phrase (§4/§8).
- ECHO, PURGE — pending (specs in docs/modules/); PULSE STARTED (scoring slice 1, above)

**Idea #3 — Anomaly-Tripwire (ORACLE anomaly → core relay → TETHER react) — COMPLETE:**

✅ COMPLETE (`37c3371`) — CHIMERA's first cross-module reflex, all four slices done
and e2e-confirmed. ⚠️ WIRE-closed, NOT autonomous: the emit is operator-triggered
(oracle.classify); auto-classify-per-event is the tail that makes it fire on its own.

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
- **3D — e2e integration** — DONE (`37c3371`): the full chain proven in one e2e
  test (real sockets) — ORACLE classify (high score) → oracle.anomaly.detected →
  broker → core relay → tether.heighten invoked; observable via tether.status
  heightened false→true. FULL spin (core + ORACLE in-process + TETHER binary), only
  seam = FakeDetector score (no Ollama). Confirmation test, not RED→GREEN
  (pass-on-write; 0 production code). 2 tests (happy + threshold-gate negative).

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

**Tooling:** `pyproject.toml` + `uv.lock` + `.venv` (Python 3.13.9); ruff + mypy (strict) + pytest configured. Direct deps: cryptography, pydantic(-settings), **ollama==0.6.2** (§6-allowed; httpx + anyio/certifi transitive). pytest markers: `integration`, `ollama`. Native C deps (Homebrew, fail-fast in each Makefile, §6 allowlist): openssl@3 + sqlite3 (CHAFF), **libsodium (VAULT crypto — XChaCha20-Poly1305/Argon2id/secure-mem)**.

**Tests:**
- Python (pytest, default): 553 passing (31 errors + 41 envelope + 36 config + 35 tokens + 36 broker + 63 lifecycle + 60 registry + 86 server [81 + 5 anomaly-relay 3B] + 12 oracle observe-first + 17 oracle Mode B + 10 oracle explainability + 8 oracle time-machine + 8 oracle NL-ask [7 ask + 1 advisory] + 3 oracle anomaly-emit [3C client-unit] + 22 pulse scoring [slice 1] + 24 pulse baseline store [slice 2] + 10 pulse assess [slice 3] + 10 pulse temporal [group B] + 3 pulse emission [EM] + 5 pulse danger-registry [DR] + 5 pulse finishers [PF] + 8 core gate [GE] + 5 core gate-wiring [GW] + 7 core override [OV] + 3 core gate-override + 5 core override.set [OS])
- Python (integration, marked — `pytest -m integration`): 37 passing (4 CHAFF + 4 MIRROR + 5 TETHER + 4 PULSE daemon + 2 PULSE danger + 2 core gate-wiring + 2 anomaly-tripwire e2e [#3 3D: ORACLE+core+TETHER full spin] + 14 ORACLE: 4 observe-first + 3 Mode B hermetic + 2 Time-Machine query + 2 NL-ask + 3 real-Ollama); the 3 real-Ollama skip when Ollama is down. NOTE: real-socket integration needs a short `--basetemp` (AF_UNIX path-too-long, see Open tails)
- Python (ollama, marked — `pytest -m ollama`): 3 passing (subset of integration; real llama3.2:1b)
- Native (CHAFF Unity): 46 passing (7 endpoints + 6 schedule + 6 crypto + 6 db + 10 jsonrpc + 6 commands + 5 generation)
- Native (MIRROR Unity): 42 passing (6 perturb + 6 profile + 5 exclude + 5 stats + 4 rng + 10 jsonrpc + 6 commands)
- Native (shim Unity): 23 passing (11 ops + 6 peercred + 2 server + 4 protocol) — separate C trust-plane suite, NOT in pytest
- Native (TETHER C++ Unity): 48 passing (4 ewma + 6 presence + 4 classify + 8 escalation + 6 emit + 10 commands + 10 monitor) — separate C++ suite, NOT in pytest
- Native (VAULT C Unity): 44 passing (6 lexer + 6 parser + 9 evaluator + 6 fail_closed + 3 relock + 7 decide + 7 crypto) — separate C suite, NOT in pytest
- Native (ECHO C Unity): 23 passing (9 shaper — budget + flat-wire invariant + burst + clamps; 7 config — defaults + validation + atomic set + budget bridge; 7 stats — padding ratio + decile histogram + surge) — separate C suite, NOT in pytest
- Native (PURGE C Unity): 16 passing (7 dry-run planner — §8 honest-wipe classify + keys-first tier plan; 9 target registry — add/dedup/remove + plan bridge) — separate C suite, NOT in pytest
- Total: 832 passing (553 default [incl 22 pulse scoring + 24 pulse baseline + 10 pulse assess + 10 pulse temporal + 3 pulse emission + 5 pulse danger-registry + 5 pulse finishers + 8 core gate + 5 core gate-wiring + 7 core override + 3 core gate-override + 5 core override.set] + 37 integration + 46 CHAFF + 23 ECHO + 16 PURGE + 42 MIRROR + 23 shim + 48 TETHER + 44 VAULT Unity; ollama subset not double-counted)

**Open tails (honest tracking, MANIFESTO §4):**
- Fernet at-rest: CHAFF (C/OpenSSL) and ORACLE (Python `cryptography.Fernet`) share the format but interop is NOT cross-tested (B1 deferred; format-faithful).
- No supervisor — CHAFF, MIRROR, and ORACLE all exit on core-disconnect (graceful, no module auto-restart yet). Core auto-restart is launchd's job (a LaunchAgent KeepAlive plist), which is SEPARATE from the §8.8 privileged-ops shim — §7.10 prose conflates the two.
- Privileged shim (§8.8) — Slice 1 NO-OP skeleton DONE (`e60e8ae`): socket SERVER + peercred (LOCAL_PEERCRED) + 4-op enum + ping/pong; peercred-only (SS-6, no secret); all 4 ops no-op (F3 — ZERO destructive effect). Scope is EXACTLY 4 root ops: lock screen (TETHER L1), evict CHIMERA Keychain (PURGE Tier 0), force-reboot (PURGE post-action), force-killall (Core §7.7 shutdown). §8.8 explicitly never opens sockets, reads files, or runs operator code; only core talks to it (per-boot shared secret — Slice 2).
- Shim Slice 2 (per-boot secret handshake) — gated on code-signing (§5.5 / Finding F2): the in-memory secret only beats a same-uid attacker once core's memory is hardened-runtime-protected. SAME code-signing tail that gates the MIRROR CGEventTap.
- Shim `ownership_apply` (SS-0(b): chmod 0660 + chown root:operatorgroup) = documented-stub — real chmod/chown is a `-m privileged`-tier follow-up (not hermetically testable, SS-7; non-root skeleton binds at umask default).
- Shim real ops (lock/evict/reboot/killall) = Slice 3+ — landed one at a time, destructive (evict/reboot) LAST and only behind the Slice 2 secret; reboot never in autotests (SH-11).
- TETHER (§5.7) — Slice 1 ENGINE (`7269080`) + daemon-wiring (`c2c0882`) + Slice 3A react-entrypoint (`994a5c4`) all done: connect→register→serve via 4A router + TICK→Monitor.step→emit + heartbeat (staged like MIRROR) + tether.heighten/relax. Monitor.step composes the engine units (EMIT-ONLY, never acts). TE-1…TE-10 decisions live in commit history; no separate design-record yet (a docs/TETHER_DESIGN.md is warranted only if it grows).
- TETHER Slice 3A react-entrypoint (`994a5c4`) — tether.heighten/relax flip a `heightened` flag; effective_grace_ms(base, heightened) applies HEIGHTEN_FACTOR=2 (grace halved → escalation requested sooner), shared by commands + Monitor; relax is an exact idempotent restore (base grace_ms never mutated); Monitor.set_heightened re-arms the ladder with the effective grace (real sync — test_heightened_escalates_sooner proves it, not a flag-only stub). Engine class untouched. EMIT-ONLY: more sensitive, never more active. This is idea #3's TETHER leaf — see the Idea #3 section. 3A = grace-only.
- TETHER escalation is EMIT-ONLY (spec §5) — engine evaluate() / Monitor.step() return a decision; CORE enforces L1→shim.lock, L2→VAULT vault.lock, L3→PURGE purge.trigger. TETHER never locks/evicts/reboots itself. Idea #3 (ORACLE anomaly → TETHER react) COMPLETE (`37c3371`): 3A (TETHER react-entrypoint) + 3B (CORE relay) + 3C (ORACLE emit) + 3D (e2e confirmation) all DONE — ORACLE emits oracle.anomaly.detected → core relays → tether.heighten, proven wire-end-to-end, NOT a TETHER subscribe (star topology clean). Path B. ⚠️ WIRE-closed, NOT autonomous — emit is operator-triggered (oracle.classify); auto-classify-per-event is the tail for autonomy. CHIMERA's first cross-module reflex.
- Anomaly-Tripwire e2e test (test_anomaly_tripwire_integration.py, #3 3D) — FULL spin (core + ORACLE in-process + the TETHER C++ binary subprocess) over real sockets; proves the chain by observing tether.status heightened false→true after a high-score oracle.classify. The only seam is FakeDetector score (no Ollama, deterministic). A confirmation test (pass-on-write), NOT RED→GREEN — pure test, 0 production code (all links were already done). Negative test covers the threshold gate (low score → no heighten).
- CORE-initiated command is a NEW capability (idea #3 3B, `666794d`): before, core only forwarded operator commands via `_route`; now `_dispatch_internal` lets core issue a command to a module on its OWN authority. ⚠️ D7 is preserved — `_dispatch_internal` is in-process only, NOT wire-reachable (no JSON-RPC method maps to it), so a module-over-the-wire invoking another module still gets -31007 (NOT_AUTHORIZED). The relay loop is the only caller; resilient (try/except → log, never crashes the consume loop).
- RELAY_RULES is declarative {event_topic → module.method}, a Server ClassVar (METHOD_TIMEOUTS precedent). One rule now: oracle.anomaly.detected → tether.heighten. Adding a tripwire = adding a row, not code. Param-mapping deferred — v1 issues the command with NO params (tether.heighten needs none); a payload→params mapper lands only when a future rule requires it.
- ⚠️ config.set → Monitor grace-sync gap (PRE-EXISTING, not introduced by 3A): tether.config.set mutates rt.escalation.grace_ms (+ presence.near_threshold), but the Monitor holds its OWN ec_ — only l3_armed is mirrored to the live Monitor (set_l3_armed). So a grace change via config.set does NOT reach the running ladder. Slice 3A heighten DOES its part correctly (set_heightened is mirrored after dispatch, beside the l3 sync); config.set's grace/near_threshold sync is a separate tail to fix (mirror config.set → Monitor too, or have Monitor read live config).
- TETHER near_threshold-heighten deferred — Slice 3A is grace-only (the escalation ladder is re-armed per ABSENT, so an effective grace applies naturally). Heightening near_threshold would need the PresenceMachine (constructed once, NOT re-armed) to read live config or be reconstructed — a later tail if anomaly-reaction should also detect absence sooner.
- TETHER GATED / out of slice: CoreBluetooth .mm BLE source (Bluetooth HW + TCC) — make_source returns an EMPTY gated CoreBluetoothSource in production (no synthetic fallback off TETHER_SYNTHETIC_RSSI — §4 never fabricates presence); IRK/companion pairing in Keychain/Secure Enclave (the SAME entitlement blocker as VAULT); real L1/L2/L3 effects (core-enforced downstream — L2 needs VAULT, L3 needs PURGE, neither built). The escalation L1/L2/L3 events have no live consumer until shim ops / VAULT / PURGE exist.
- ✅ TE-7b (4 jsonrpc copies, chaff→mirror→shim→tether) — RESOLVED by the JE-1 extract (chaff `24cf41f` pilot + mirror `611c16c` + shim `c25dfec` + tether `2245f09`). The 4 copies are now ONE canonical `modules/common/jsonrpc.{h,c}`; drift eliminated (each was byte-identical modulo its `<MOD>_result_t` namespace — proven per migration by normalized-diff = only the top comment). C++ tether links the C unit via the common header's `extern "C"` (compiled C `clang -std=c17`, linked clang++). No longer a debt.
- AF_UNIX path-too-long (env, NOT code) — real-socket integration (server `TestRealSocket*`, MIRROR, TETHER) binds UNIX sockets under pytest tmp_path; on macOS the default `TMPDIR` (`/var/folders/.../T`, ~48 chars) + pytest dirs + long test names exceeds the ~104-char `AF_UNIX` limit → 18 default `test_server.py` failures + integration breakage. Fix is ENV: `TMPDIR=/tmp/t` for default, `--basetemp=/tmp/tt` for `-m integration`. Confirmed artifact (438 default + 5 TETHER integration green with short paths). Future: a conftest could pin a short socket dir.
- Packet-plane root is a SEPARATE track, NOT the §8.8 shim: CHAFF Phase A (pf/dtrace) and ECHO (pfctl/BPF/raw socket) need packet-level root, which §8.8 forbids — future §8 amendment or a dedicated packet-helper. CHAFF code returns required_capability='privileged_shim' for profile.*, but §8.8 grants no such capability — spec gap to resolve before that path unblocks.
- ⚠️ VAULT has TWO blockers (CORRECTED — the design-pass caught that the earlier "blocker = entitlements, NOT root" claim was wrong): (1) **entitlements** — Keychain / Secure-Enclave + TCC + code-signing — for the per-vault master secret (the §8.8 shim does not grant this; it only evicts Keychain for PURGE); AND (2) **root** — `mount_tmpfs` exists on this macOS (`/sbin/mount_tmpfs`, Darwin 25) but `mount(2)` needs root, so VAULT's tmpfs mount is privileged. Resolve at the mount-slice: a shim op, an hdiutil `ram://` alternative, or a dedicated helper. The earlier single-blocker claim is retracted.
- VAULT slice 1 (policy DSL engine, `655f183`) + DEFER (`165a1de`) + crypto (`e82f69b`) DONE — evaluator (full ALLOW/DENY/DEFER, fail-closed) + crypto engine (XChaCha20-Poly1305 + Argon2id + secure-mem). `vault_eval` stays the instantaneous ALLOW/DENY (slice-1 contract, 30 tests intact); `vault_decide` is the DEFER entrypoint (no test-fit). The crypto slice ended the pure-C phase (libsodium, deliberately). Remaining slices, ALL gated/platform: Keychain/Enclave master secret (entitlements), mount (catch 2 — root), kqueue relock, IPC/daemon (catch 3 RESOLVED — `modules/common/jsonrpc` extracted (JE-1); the daemon-slice now just LINKS common, no copy). The crypto engine is the foundation; the gated pieces sit on top. ⚠️ daemon-slice UNBLOCKED on jsonrpc, but still gated on Keychain/Enclave master secret + mount (catch 2 — root) — NOT closed.
- VAULT DEFER precision is 1h (the context's finest clock field is `hour`) → defer_seconds is always a multiple of 3600; day_of_month rolls naively (no month calendar) and boot-second projection is coarse, both bounded by the 7-day cap (DEFER_CAP_STEPS=168). Finer resolution would need a minute/second field in the context — a documented tail.
- ✅ VAULT catch 1 — RESOLVED (`a038979` + `e82f69b`): libsodium chosen (Argon2id + XChaCha20-Poly1305 + first-class secure memory); CLAUDE.md §6 amended to a per-module C allowlist (the old "libcurl only" was already false — CHAFF links openssl@3+sqlite3). CommonCrypto rejected (PBKDF2-only = KDF downgrade); openssl@3 was a viable zero-new-dep runner-up but libsodium's secure-memory + spec intent won. No longer open.
- ✅ VAULT spec corrections — RESOLVED in spec (`a038979`, not just code): catch A (key_salt was "rotated per unlock" → STABLE, stored in metadata, rotated only on re-encrypt — a per-unlock salt makes stored ciphertext undecryptable) and catch B (nonce was unspecified → 192-bit random per seal, stored). AEAD changed AES-256-GCM → XChaCha20-Poly1305 with the rationale recorded in-spec. The spec is now truthful.
- VAULT crypto fail-closed + no-leak (`e82f69b`): the raw master secret lives only in sodium_malloc secure memory during derive and is wiped immediately (no swap / core-dump leak — VAULT's thesis, in code). open verifies the Poly1305 tag before releasing plaintext and actively sodium_memzero's pt_out on any failure (wrong key / tamper).
- ⭐ VAULT tamper-test assertion corrected (`e82f69b`) — NOT test-fitting (same class as TETHER's test_present_from_fringe: impl design-correct, the test encoded the wrong post-condition). The RED test asserted a specific sentinel byte survived after a failed open (out[0]==0xAA), but the agreed defensive active-wipe (design-pass nuance 3) zeroes pt_out on failure. The real invariant is "no plaintext leak", not a sentinel — corrected to `memcmp(out, pt, ptlen) != 0` (impl-agnostic: holds whether wiped to 0 or left untouched).
- ✅ VAULT catch 3 — jsonrpc 5th copy — RESOLVED: `modules/common/jsonrpc` now EXISTS (JE-1 extract). VAULT's daemon-slice will LINK common as the FIRST new consumer (D1=C done), never a 5th copy. The trigger fired ahead of VAULT — the extract was done proactively across the existing 4 modules.
- vault.lock (§6) is the TETHER L2 escalation target — when VAULT's daemon + vault.lock land, core can enforce TETHER L2 (tether.escalation → vault.lock), giving #3's L2 a live consumer (currently L2/L3 escalation events have none). Nuance: vault.lock takes {vault_id}; routing an escalation to it means "lock the currently-open vault" — a downstream wiring detail for that slice.
- 0 of 8 native modules NOT started — ALL 8 ORGANS UNDERWAY. CHAFF + MIRROR + ORACLE done; PURGE started (dry-run planner `1481d6d` + target registry `aea7b86` — honest-wipe classify + tier plan + Tier-2 target list; ⚠️ real destruction Keychain/Mach VM/dc zva/libsodium/daemon gated); ECHO started (shaper `ca06b25` + config `2f381ce` + stats `a0a8014` — padding math + operator knobs + accounting; pure LOGIC complete; ⚠️ pf/BPF I/O + IPC daemon gated/deferred); TETHER started (engine + daemon-wiring + Slice 3A); VAULT started (policy + DEFER + crypto; Keychain/mount/daemon gated); PULSE started (scoring slice 1 `d9b0a42` + baseline store slice 2 `bef89a6` + assess wiring slice 3 `54b2751` + temporal group B `abd2bf3` + daemon `44280d2` + mode.changed emission `76e9955` + danger-registry `b87be5a`; ⚠️ NOT complete — LIVE module (registers, serves pulse.* incl danger-registry, emits pulse.mode.changed) but live signal collection (MIRROR group-A / kqueue idle / ORACLE drift) STILL gated (§6 method surface COMPLETE incl calibrate + pulse.error `53547ad`) + core gate-enforcement — DECISION (`core/gate.py` `7d6c8fa`) + LIVE WIRING (`fbe64cc`: block/delay in `_route` + mode-track + danger-refresh) done + override-phrase storage (`3564968`: PBKDF2 store, gate honors `_override`, secret stripped) done + operator set-phrase (`22aebc7`: core.override.set, surface-only) done; ⚠️ confirm-dialog (surface) + external-OS gating (CLI/shell) + live registry-refresh + change-requires-old-phrase still deferred).
- MIRROR CGEventTap install — GATED on code-signing + Accessibility TCC (§6/§9); mirror.enable returns -31004 until then. The code-signing tail is now shared across MIRROR (tap), shim Slice 2 (secret in hardened-runtime memory), and TETHER (CoreBluetooth TCC + IRK in Keychain).
- MIRROR no event producer yet — daemon wiring done, but drain_events is only a forward-compat seam (queue empty); events ship when the tap lands.
- MIRROR → PULSE aggregate-event gap (D8) — PULSE expects a periodic aggregate event MIRROR doesn't yet define; address at PULSE time.
- jsonrpc — ✅ EXTRACTED to `modules/common/` (JE-1; see the resolved TE-7b tail). ipc is NOT extracted: it diverges by role/language — chaff/mirror have a C client `ipc.c`, tether a C++ `ipc.cpp`, shim has no ipc (inline socket server). ipc stays per-module; only jsonrpc was the clean shared target.
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
