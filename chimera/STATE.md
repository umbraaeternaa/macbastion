# CHIMERA — Project State Snapshot

> Updated: 2026-06-04
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
GREEN, Mode B GREEN) done.
Last completed: **ORACLE Mode B** (commit `d754fb1`) — oracle.classify runs a real
local LLM (llama3.2:1b Q8_0 via Ollama, structured output) to score event anomaly
with the baseline as context. Manual, advisory-only (returns score, no act/emit).
ORACLE is now fully implemented (Mode A learning + Mode B classify).

**Skeleton scope check (MANIFESTO §4 — honest accounting):**

Core skeleton v0.2.0 (§7.12) lists: socket server, router, broker, registry,
capability-token issuer, AND a privileged shim (§7.10 / §8.8 — a separate
C/LaunchDaemon for elevated operations, not among the 8 Python `core/` modules).

- Python `core/`: 8/8 modules done ✓
- Privileged shim: NOT YET started ⚠️

**ETAP 2 verdict:** Python core skeleton complete. The privileged shim is a
prerequisite for native modules requiring elevated capabilities (VAULT, PURGE,
etc.) and will be addressed before or alongside ETAP 3 (native modules).

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
  status.model from startup probe; classifications_today in-memory. Reuses
  core.envelope + core.errors only (D1=c). 29 unit + 8 integration (1 real-Ollama,
  -m ollama). ruff + mypy --strict clean. ORACLE fully done (Mode A + Mode B). —
  Mode B GREEN (`d754fb1`)
- ECHO, PULSE, VAULT, TETHER, PURGE — pending (specs in docs/modules/)

`chimera/proto/` — still empty (`.gitkeep`).

**Tooling:** `pyproject.toml` + `uv.lock` + `.venv` (Python 3.13.9); ruff + mypy (strict) + pytest configured. Direct deps: cryptography, pydantic(-settings), **ollama==0.6.2** (§6-allowed; httpx + anyio/certifi transitive). pytest markers: `integration`, `ollama`.

**Tests:**
- Python (pytest, default): 412 passing (31 errors + 41 envelope + 36 config + 35 tokens + 36 broker + 63 lifecycle + 60 registry + 81 server + 12 oracle observe-first + 17 oracle Mode B [3 prompt + 4 llm + 6 detector + 4 baseline])
- Python (integration, marked — `pytest -m integration`): 16 passing (4 CHAFF + 4 MIRROR + 8 ORACLE: 4 observe-first + 3 Mode B hermetic + 1 real-Ollama)
- Python (ollama, marked — `pytest -m ollama`): 1 passing (subset of integration; real llama3.2:1b)
- Native (CHAFF Unity): 46 passing (7 endpoints + 6 schedule + 6 crypto + 6 db + 10 jsonrpc + 6 commands + 5 generation)
- Native (MIRROR Unity): 42 passing (6 perturb + 6 profile + 5 exclude + 5 stats + 4 rng + 10 jsonrpc + 6 commands)
- Total: 516 passing (ollama subset not double-counted)

**Open tails (honest tracking, MANIFESTO §4):**
- Fernet at-rest: CHAFF (C/OpenSSL) and ORACLE (Python `cryptography.Fernet`) share the format but interop is NOT cross-tested (B1 deferred; format-faithful).
- No supervisor — CHAFF, MIRROR, and ORACLE all exit on core-disconnect (graceful, no module auto-restart yet). Core auto-restart is launchd's job (a LaunchAgent KeepAlive plist), which is SEPARATE from the §8.8 privileged-ops shim — §7.10 prose conflates the two.
- Privileged shim (§8.8) — not started. Scope is EXACTLY 4 root ops: lock screen (TETHER L1), evict CHIMERA Keychain (PURGE Tier 0), force-reboot (PURGE post-action), force-killall (Core §7.7 shutdown). §8.8 explicitly never opens sockets, reads files, or runs operator code; only core talks to it (per-boot shared secret).
- Packet-plane root is a SEPARATE track, NOT the §8.8 shim: CHAFF Phase A (pf/dtrace) and ECHO (pfctl/BPF/raw socket) need packet-level root, which §8.8 forbids — future §8 amendment or a dedicated packet-helper. CHAFF code returns required_capability='privileged_shim' for profile.*, but §8.8 grants no such capability — spec gap to resolve before that path unblocks.
- VAULT's blocker is Keychain / Secure-Enclave entitlements (code-signing + TCC), not root — the §8.8 shim does not unblock VAULT (it evicts Keychain for PURGE, it does not grant access).
- 5 of 8 native modules pending (ECHO, PULSE, VAULT, TETHER, PURGE) — CHAFF + MIRROR + ORACLE done.
- MIRROR CGEventTap install — GATED on code-signing + Accessibility TCC (§6/§9); mirror.enable returns -31004 until then.
- MIRROR no event producer yet — daemon wiring done, but drain_events is only a forward-compat seam (queue empty); events ship when the tap lands.
- MIRROR → PULSE aggregate-event gap (D8) — PULSE expects a periodic aggregate event MIRROR doesn't yet define; address at PULSE time.
- ipc/jsonrpc duplicated chaff ↔ mirror (D1=C — extract to modules/common/ at the next *C* native module; ORACLE is Python, so it did not trigger it).
- ORACLE classify is baseline-aware (context = recent_events + summary), advisory-only — returns score, never acts/emits.
- ORACLE classifications_today is in-memory and approximate (no day-rollover).
- ORACLE mid-call Ollama death surfaces as a generic error, not -31004 (startup probe + per-ConnectionError catch cover the typical down cases).
- ORACLE next slices (NOT in Mode B): auto-classify per event + oracle.anomaly.detected emission + similar_past_events (top-3) + oracle.model.swap.
- ORACLE real event input is CHAFF only — MIRROR emits nothing yet, so chaff.* is the sole live source feeding the baseline.
- ORACLE standalone `python -m oracle` needs modules/oracle on PYTHONPATH (proper editable-package install is a follow-up; __main__ cannot self-fix the import path).
- ORACLE client.py (D1=c, Python) carries a TODO to extract a shared Python module-client at the 2nd Python module (mirror of the C D1=C duplication).
