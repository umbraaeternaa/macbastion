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
(Router 4A), Step 2 (CHAFF: 2A bootstrap, 2B RED, 2C GREEN, 2D daemon + integration) done;
MIRROR (second native module: bootstrap, RED, engine GREEN) underway. Last
completed: **MIRROR engine GREEN** (commit `b9d4fdf`) — perturbation engine +
mirror.* dispatch done; daemon wiring + CGEventTap install pending.

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

**Native modules (`chimera/modules/`) — 2 of 8 started:**
- `chaff` (§5.1) — first native module, working daemon. C17 + ARM64 (Make +
  vendored Unity/cJSON); connects to core, registers + heartbeats, serves chaff.*
  via the 4A router, emits events, generates decoy HTTPS traffic (two pthread
  threads, poll-based IPC, openssl Fernet, SQLite). 46 Unity + 4 integration
  (hermetic). binary -Werror clean. Phase A (profiling) deferred to the
  privileged shim (pf/dtrace = root). — Phase B daemon DONE (`4f443f5`)
- `mirror` (§5.4) — second native module, perturbation engine + dispatch done.
  C17 (Make + vendored Unity/cJSON, frameworks only — no curl/sqlite/openssl).
  Engine: Box-Muller gaussian mouse noise, uniform timing jitter (clamp ≥0), §3
  presets (light/medium/heavy), secure-field downgrade to light, fixed-capacity
  exclusion list, cumulative per-event-type stats (§7 — counts only). mirror.*
  dispatch: status/profile.set/exclude.add|remove|list/stats/disable;
  mirror.enable GATED → -31004 (code-signing + Accessibility TCC, §6/§9).
  ipc/jsonrpc copied from chaff (D1=C). 42 Unity, binary -Werror clean. Daemon
  wiring (IPC thread + registration + events) + CGEventTap install PENDING. —
  engine GREEN (`b9d4fdf`)
- ECHO, ORACLE, PULSE, VAULT, TETHER, PURGE — pending (specs in docs/modules/)

`chimera/proto/` — still empty (`.gitkeep`).

**Tooling:** `pyproject.toml` + `uv.lock` + `.venv` (Python 3.13.9); ruff + mypy (strict) + pytest configured.

**Tests:**
- Python (pytest, default): 383 passing (31 errors + 41 envelope + 36 config + 35 tokens + 36 broker + 63 lifecycle + 60 registry + 81 server)
- Python (integration, marked — `pytest -m integration`): 4 passing (CHAFF daemon E2E vs live core, hermetic)
- Native (CHAFF Unity): 46 passing (7 endpoints + 6 schedule + 6 crypto + 6 db + 10 jsonrpc + 6 commands + 5 generation)
- Native (MIRROR Unity): 42 passing (6 perturb + 6 profile + 5 exclude + 5 stats + 4 rng + 10 jsonrpc + 6 commands)
- Total: 475 passing

**Open tails (honest tracking, MANIFESTO §4):**
- CHAFF Fernet ↔ Python `cryptography.Fernet` interop NOT cross-tested (B1 deferred; format-faithful).
- No supervisor — CHAFF exits on core-disconnect (graceful, but no auto-restart until the launchd shim lands).
- Privileged shim (§7.10/§8.8) — not started; blocks CHAFF Phase A + ECHO/VAULT/TETHER/PURGE.
- 6 of 8 native modules pending (ECHO, ORACLE, PULSE, VAULT, TETHER, PURGE) — CHAFF + MIRROR engine done.
- MIRROR daemon wiring — IPC thread + core registration + event emission, not started (engine done, not yet a running daemon).
- MIRROR CGEventTap install — GATED on code-signing + Accessibility TCC (§6/§9); mirror.enable returns -31004 until then.
- MIRROR → PULSE aggregate-event gap (D8) — PULSE expects a periodic aggregate event MIRROR doesn't yet define; address at PULSE time.
- ipc/jsonrpc duplicated chaff ↔ mirror (D1=C — extract to modules/common/ at the third native module).
