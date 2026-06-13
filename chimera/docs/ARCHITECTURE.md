# CHIMERA — Architecture (§1–§8, all five parts)

> Жива технічна біблія проекту. Оновлюється з кожним архітектурним рішенням.
> Версія: 0.1.0-alpha (genesis)

---

## §1. Загальна філософія

CHIMERA — не набір інструментів. Це **організм**.
Кожен модуль (орган) робить одну річ. **Мозок (core)** їх координує.
Цінність — в координації, не в окремих органах.

Базова метафора:

```
   +-------------------------------------+
   |              USER (TY)              |
   |    (видає команди, отримує статус)  |
   +------------------+------------------+
                      |
                      v
   +-------------------------------------+
   |        CHIMERA CORE (Python)        |
   |  +-------------------------------+  |
   |  |  Event loop (asyncio)         |  |
   |  |  State store (SQLite + AES)   |  |
   |  |  IPC server (UNIX socket)     |  |
   |  |  Module registry & lifecycle  |  |
   |  |  Local LLM (Ollama+Llama 1B)  |  |
   |  +-------------------------------+  |
   +------------------+------------------+
                      |  JSON-RPC over UNIX socket
       +--------+-----+-----+--------+--------+
       |        |           |        |        |
       v        v           v        v        v
   +--------+ +--------+ +--------+ +--------+ +--------+
   | CHAFF  | |  ECHO  | | ORACLE | | MIRROR | | PULSE  |
   |  (C)   | |  (C)   | | (Py)   | |  (C)   | |  (C)   |
   +--------+ +--------+ +--------+ +--------+ +--------+
       |        |           |        |        |
       v        v           v        v        v
   +-------------------------------------------------+
   |        macOS kernel / network stack             |
   +-------------------------------------------------+

   +--------+  +--------+  +--------+
   | VAULT  |  | TETHER |  | PURGE  |    <- event-driven
   |  (C)   |  |  (C++) |  | (C+Asm)|       organs, not
   +--------+  +--------+  +--------+       always running
```

---

## §2. Стек і відповідальність

| Шар             | Технологія                  | Відповідальність                   |
|-----------------|-----------------------------|------------------------------------|
| **UX/CLI**      | Python 3.11 + Click + Rich  | Користувацький інтерфейс           |
| **Orchestrator**| Python 3.11 + asyncio       | Event loop, IPC server, координація|
| **State**       | SQLite + Fernet (AES-128)   | Persistent encrypted state         |
| **Reasoning**   | Ollama + Llama 3.2 1B       | Local LLM для anomaly detection    |
| **Modules**     | C17, C++20, ARM64 Asm       | Native daemons                     |
| **IPC**         | UNIX socket + JSON-RPC 2.0  | Comm між core і модулями           |
| **Build**       | Make + clang                | Native compilation                 |
| **UI**          | SwiftBar plugin             | Status в menu bar                  |

---

## §3. Принципи проектування

1. **Одна задача — один модуль.** Якщо два модулі починають робити схоже —
   обʼєднуємо або виділяємо спільне в core.

2. **Модулі не знають один про одного.** Спілкуються тільки через core.
   Це дозволяє замінити будь-який модуль без зачіпання решти.

3. **Core нічого не робить сам.** Тільки координує. Якщо в core
   зʼявляється бізнес-логіка — це знак що треба новий модуль.

4. **Fail closed.** Якщо щось ламається — система йде в більш захищений
   стан, не в менш захищений. Якщо CHAFF умирає — трафік не іде
   "як зазвичай", а блокується до перезапуску.

5. **No-network policy.** Жоден компонент CHIMERA не робить HTTP-запитів
   назовні. Виключення тільки для CHAFF (це його робота — генерувати трафік).

---

## §4. Що йде далі в цьому документі

- **§5.** Детальна специфікація кожного з 8 модулів (Part 2)
- **§6.** IPC протокол: JSON-RPC схеми (Part 3)
- **§7.** Module lifecycle: registration, health, shutdown (Part 4)
- **§8.** Security model: загрози, захист, обмеження (Part 5)

---

**Status:** All five parts complete (§1–§8). Specification phase done; next is core skeleton code (v0.2.0) and OPSEC.md.

---

# §6 IPC Protocol

> Part 3 of 5. Foundation for all module implementations — must land before any module code.
> Decisions anchored by: chimera/docs/UX.md (hybrid CLI + swiftbar + event stream)

---

## 6.1 Purpose

Defines how CHIMERA's components communicate: CLI to core, swiftbar to core, event-stream listeners to core, modules to core, and module to module (always relayed through core, never direct).

One wire format (JSON-RPC 2.0 over NDJSON), two interaction models (synchronous request/response and asynchronous pub/sub), one broker (core).

Every IPC table in the module specifications (§5.1–§5.6, and forthcoming §5.7–§5.8) is a consumer of this protocol. Where a module spec and this section disagree, this section is authoritative.

---

## 6.2 Topology — star, not mesh

Core is the only hub. Modules NEVER connect to each other. Every cross-module signal — PULSE consuming ORACLE anomalies, VAULT checking TETHER presence, PULSE reading MIRROR aggregates — is relayed by core.

```
   ┌──────┐   ┌──────────┐   ┌────────────┐
   │ CLI  │   │ swiftbar │   │ event-strm │      surfaces
   └──┬───┘   └────┬─────┘   └─────┬──────┘
      └────────────┼───────────────┘
                ┌──▼───┐
                │ CORE │   hub: router + broker + registry
                └──┬───┘
   ┌──────────┬────┼─────────┬──────────┐
┌──▼──┐   ┌───▼──┐ │    ┌────▼───┐  ┌───▼────┐
│CHAFF│ … │ORACLE│ │    │ VAULT  │  │ PULSE  │   modules
└─────┘   └──────┘ │    └────────┘  └────────┘
                ┌──▼───┐
                │ ECHO │ …
                └──────┘
```

Rationale: a star gives a single audit point, a single security boundary, and keeps each module simple (one connection, one peer). A mesh of 8 modules would require up to 28 pairwise connections, each with its own authentication and trust relationship — unmanageable. The cost is that core is a single point of failure; this is mitigated by the supervisor and restart policy defined in §7 (lifecycle).

---

## 6.3 Transport

- **UNIX domain sockets only.** No TCP, no network surface. Filesystem permissions are the first authentication layer.
- **Two sockets**, separating command traffic from event traffic so a slow event consumer can never block command latency:
  - `~/.config/chimera/run/core.sock` — request/response commands
  - `~/.config/chimera/run/events.sock` — event subscription + push stream
- **Direction:** core listens (server); every module and surface connects out to core (client) on startup.
- **Permissions:** socket files mode `0600` (owner-only). The `run/` directory mode `0700`.
- **Framing:** newline-delimited JSON (NDJSON) — exactly one JSON object per line, terminated by `\n`. Embedded newlines in string values are escaped per JSON (`\n`), so the framing is unambiguous.

Rationale for NDJSON over a binary framing: CHIMERA is a power tool for a deliberate operator (MANIFESTO §6). Being able to run `socat - UNIX:~/.config/chimera/run/core.sock` and read the traffic with your own eyes is worth more than the marginal efficiency of length-prefixed binary on a localhost socket.

---

## 6.4 Wire format — JSON-RPC 2.0

All four message shapes are standard JSON-RPC 2.0.

Request (surface to core, or core to module):
```
{"jsonrpc":"2.0","id":42,"method":"vault.unlock","params":{"vault_id":"work-docs"}}
```

Response, success:
```
{"jsonrpc":"2.0","id":42,"result":{"ok":true,"mount_path":"/tmp/...","relock_in_sec":900}}
```

Response, error:
```
{"jsonrpc":"2.0","id":42,"error":{"code":-31003,"message":"denied by policy","data":{"reason":"pulse_mode_required_normal"}}}
```

Notification (event — no `id`, no response expected):
```
{"jsonrpc":"2.0","method":"oracle.anomaly.detected","params":{"severity":0.82,"reasoning":"...","origin":"oracle"}}
```

CHIMERA conventions layered inside `params`/`result` (never breaking JSON-RPC):
- Every request carries `"ts": <unix_micros>` for ordering and audit.
- Every event that core relays after fan-out carries `"origin": "<module>"` so subscribers know the true source module even though the message arrives from core.

---

## 6.5 Error codes

JSON-RPC reserved range (used as-is):

| Code   | Meaning           |
|--------|-------------------|
| -32700 | parse error       |
| -32600 | invalid request   |
| -32601 | method not found  |
| -32602 | invalid params    |
| -32603 | internal error    |

CHIMERA application range (`-31000` block):

| Code   | Meaning              | Typical cause                                            |
|--------|----------------------|----------------------------------------------------------|
| -31000 | module offline       | target module not registered with core                   |
| -31001 | module timeout       | module did not answer within the method deadline         |
| -31002 | capability missing   | module is up but does not advertise this method          |
| -31003 | denied by policy     | VAULT policy DENY, PULSE gate block, etc.                |
| -31004 | precondition failed  | e.g. another vault already unlocked                      |
| -31005 | fail-closed          | a required dependency module is offline; safe default    |
| -31006 | rate limited         | backpressure; caller should retry later (see §6.8)       |
| -31007 | not authorized       | caller's capability token does not grant this method     |

---

## 6.6 Event subscription model

A subscriber (swiftbar, the event-stream listener, or a module such as PULSE) subscribes over `events.sock`:
```
{"jsonrpc":"2.0","id":1,"method":"core.subscribe","params":{"topics":["oracle.*","vault.locked","tether.*"]}}
```

Core replies with a subscription id, then pushes every matching notification on that connection until the subscriber unsubscribes or disconnects.

Topic syntax is dot-namespaced with `*` as a single- or multi-level wildcard:

| Pattern    | Matches                                              |
|------------|------------------------------------------------------|
| `oracle.*` | `oracle.anomaly.detected`, `oracle.baseline.updated` |
| `*.error`  | every module's `error` event                         |
| `vault.locked` | exactly that event                               |
| `*`        | firehose — audit/debug only                          |

swiftbar uses both models at once: it subscribes to critical topics for instant push, AND polls `core.status` every 5 seconds for a complete state snapshot. Push gives urgency; poll guarantees completeness even after a dropped event (see §6.8).

---

## 6.7 Capability negotiation & registry

On startup, each module registers with core:
```
{"jsonrpc":"2.0","id":1,"method":"core.register","params":{
   "module":"vault","version":"0.7.0",
   "methods":["vault.unlock","vault.lock","vault.create","vault.list","..."],
   "events":["vault.unlocked","vault.locked","vault.denied","..."],
   "depends_on":["pulse","tether"]}}
```

Core maintains a live registry of every registered module: its version, advertised methods, advertised events, declared dependencies, and current status. Any caller can query it:
```
{"jsonrpc":"2.0","id":2,"method":"core.capabilities"}
→ {"vault":{"version":"0.7.0","status":"up","methods":[...],"events":[...]}, ...}
```

The registry is load-bearing in three places already specified:
- **VAULT's policy evaluator** checks whether PULSE/TETHER are registered and up; if a policy references `pulse_mode` and PULSE is absent, evaluation fails closed with `-31005`.
- **CLI tab-completion** enumerates available methods from the registry.
- **swiftbar** shows exactly the modules that are registered, nothing hardcoded.

Versioning is capability-based, not strict-semver: a caller checks whether a method exists before calling it (`-31002` if not), rather than requiring core and module versions to match. This lets modules evolve independently — important for a project built "for a year, not a week" (MANIFESTO §7).

---

## 6.8 Backpressure & timeouts

Timeouts:
- Every request has a deadline. Default 5 s, overridable per method. ORACLE `classify` gets 30 s (LLM inference); `vault.unlock` gets 10 s (Argon2id derivation).
- On deadline expiry, core returns `-31001 module timeout` to the caller and does NOT hang. The caller is never blocked indefinitely.

Event fan-out backpressure:
- Each subscriber connection has a bounded ring buffer (default 256 events).
- On overflow, core drops the OLDEST event and emits a single `core.overflow` notification to that subscriber, telling it how many events were missed.
- This means a slow consumer (e.g. a stalled swiftbar) can never block a fast producer (e.g. CHAFF emitting decoy events). The slow consumer loses some events but is told it did — and recovers full state via the next `core.status` poll.

Rationale: bounded loss with notification beats unbounded blocking. One slow subscriber must never cause a cascading stall across the whole event system.

---

## 6.9 Authentication

Two layers, defense in depth:

1. **Filesystem.** `0600` sockets in a `0700` directory mean only the owner's processes can connect at all. This stops other local users.

2. **Per-connection capability tokens.** On connect, core issues an ephemeral, in-memory token scoped to the connecting peer:
   - **Surfaces** (CLI, swiftbar, event-stream) receive a full token: all methods.
   - **Modules** receive a scoped token: a module may emit its own events and call `core.*` methods, but may NOT call another module's methods. CHAFF cannot call `vault.unlock`; ORACLE cannot call `purge.*`.
   - A call outside the token's scope returns `-31007 not authorized`.
   - The token lives only for the connection's lifetime and dies on disconnect. Nothing is persisted.

This ensures that a single compromised module cannot drive the others. Filesystem permissions defend against foreign users; capability tokens defend against a subverted insider module.

---

## 6.10 Lifecycle hooks (handoff to §7)

§6 defines the wire; §7 will define the full module lifecycle (start order, health policy, restart, graceful shutdown). §6 specifies only the three lifecycle messages that ride this protocol:

- `core.register` — module announces birth and capabilities (§6.7)
- `core.heartbeat` — module proves liveness; default every 10 s; missing N heartbeats marks the module `down` in the registry
- `core.deregister` — module announces graceful shutdown

Detailed lifecycle semantics (what core does when heartbeats stop, restart backoff, dependency-aware start order) are deferred to §7.

---

## 6.11 Status

**Specification.** No code yet.

This is the foundation every module implementation depends on. The CHIMERA core skeleton (socket server, router, broker, registry, token issuer) is the first code to be written, targeted at chimera v0.2.0 — it must land before any individual module's code.

No imitations. No stubs. (See MANIFESTO §4.)

---

# §7 Module Lifecycle

> Part 4 of 5. Defines how core manages each module across its life.
> Builds on §6 IPC (core.register / core.heartbeat / core.deregister hooks).

---

## 7.1 Purpose

§6 defined the wire; §7 defines what flows through it over a module's lifetime: startup order, registration, liveness detection, failure handling, restart policy, dependency cascades, and graceful shutdown.

The governing principle for every failure path in this section: **when state is uncertain, CHIMERA locks down, never opens up.** A failure can only make the system more closed, never less. This is fail-safe, not fail-open.

---

## 7.2 Lifecycle states

From core's view, each module is always in exactly one state:

```
UNREGISTERED → STARTING → REGISTERED → HEALTHY ⇄ DEGRADED
                                           │
                                           ↓
                                      STOPPING → STOPPED
                                           │
                                       (crash)
                                           ↓
                                       FAILED → (restart) → STARTING
```

| State        | Meaning                                                      |
|--------------|--------------------------------------------------------------|
| UNREGISTERED | core knows the module should exist; no connection yet        |
| STARTING     | process launched, not yet registered                         |
| REGISTERED   | sent `core.register`; capabilities known                     |
| HEALTHY      | heartbeats arriving on time, self-check ok                   |
| DEGRADED     | heartbeats late, or module self-reports degraded             |
| STOPPING     | graceful shutdown in progress                                |
| STOPPED      | clean exit; `core.deregister` received                       |
| FAILED       | crashed, heartbeat lost, or killed                           |

---

## 7.3 Startup order — dependency-aware

Modules declare `depends_on` in `core.register` (§6.7). Core computes a topological order and starts them in waves. A module starts only after all its declared dependencies are HEALTHY.

```
Wave 0 (no deps):   core, then CHAFF, ECHO, MIRROR, ORACLE
Wave 1 (need core): PULSE (needs MIRROR), VAULT
Wave 2:             TETHER (needs VAULT for L2, PURGE for L3)
Wave 3:             PURGE (target of TETHER L3)
```

- If a dependency does not reach HEALTHY within a startup timeout, the dependent stays UNREGISTERED; core logs it and surfaces it. Core does NOT hang waiting (fail-closed, not fail-stuck).
- Circular dependencies are rejected at config-load time — the dependency graph must be a DAG.

---

## 7.4 Heartbeat & liveness

Liveness ("is the module alive") is distinct from a module's internal work tick ("how often it does its job"). TETHER may scan BLE every 2s internally, but core only asks for liveness every 10s.

- Each module sends `core.heartbeat` every `HEARTBEAT_INTERVAL` (default 10s).
- Core tracks last-seen per module. Missed-heartbeat thresholds:

| Missed        | Elapsed | Core action                          |
|---------------|---------|--------------------------------------|
| 1             | >10s    | none (jitter tolerance)              |
| 2             | >20s    | mark DEGRADED, emit `module.degraded`|
| 3             | >30s    | mark FAILED, begin restart policy    |

- Heartbeat carries lightweight self-status: `{module, seq, uptime_s, self_check: ok|warn|fail, queue_depth}`.
- A module may self-report `fail` even while heartbeats arrive (e.g. ORACLE reports Ollama unreachable). Core then marks it DEGRADED regardless of heartbeat timing.

---

## 7.5 Restart policy — exponential backoff with cap

On FAILED, core restarts the module with backoff:

```
attempt 1: wait 1s
attempt 2: wait 2s
attempt 3: wait 4s
attempt 4: wait 8s
attempt 5+: wait 30s (capped)
```

- After `MAX_RESTARTS` (default 5) within a rolling 1-hour window, core gives up: marks the module PERMANENTLY_FAILED, emits `module.dead`, and requires operator intervention.
- Restart preserves nothing in-process. Modules are stateless across restarts except for their own encrypted on-disk state, which they reload themselves (§7.8).
- Dependents of a FAILED module react per §7.6.

---

## 7.6 Dependency failure cascade

When a module becomes FAILED or DEGRADED, its dependents react — and the reaction can only ever make the system more locked:

- **VAULT depends on PULSE / TETHER** for policy predicates. If PULSE dies while a vault is unlocked, the vault's policy is re-evaluated; the missing predicate fails closed and the vault relocks immediately (§7 decision: fail-closed, no grace).
- **TETHER depends on VAULT (L2) and PURGE (L3).** If PURGE is dead when TETHER L3 would fire, TETHER CANNOT escalate to L3. It logs, falls back to L2 (lock all vaults), and raises a loud alert. A dead PURGE can never cause data loss.
- **Core never auto-triggers a destructive cascade.** A dependency death can lock vaults, pause traffic, or hold state — it can never trigger PURGE or any irreversible action. The cascade invariant: failures escalate toward MORE locked, never toward destruction.

---

## 7.7 Graceful shutdown

On operator stop or system shutdown:

```
1. Core broadcasts core.shutdown to all modules
2. Shutdown proceeds in REVERSE dependency order (dependents first):
   TETHER → VAULT → PULSE → ORACLE/MIRROR/ECHO/CHAFF
3. Each module: finish in-flight work, flush state, send core.deregister
4. Grace period SHUTDOWN_TIMEOUT (default 5s) per module
5. Modules not deregistered in time → SIGTERM, then SIGKILL
6. VAULT relocks all open vaults BEFORE it deregisters
7. PURGE: shutdown is NOT a purge — it simply stops the daemon
8. Core exits last, after confirming all modules stopped
```

---

## 7.8 Crash safety & state recovery

- Each module owns its on-disk state and its encryption (defined per module spec). On restart, a module reloads its own state — ORACLE its baseline, PULSE its history, VAULT its metadata. Core never holds module state.
- Core's registry is rebuilt from re-registration, not persisted. When core restarts, modules detect the dropped connection and re-register.
- **If CORE crashes**, modules do NOT continue autonomously. They enter a fail-safe holding pattern: CHAFF and ECHO pause traffic shaping, VAULT relocks all open vaults, TETHER holds its last presence state without escalating, ORACLE and PULSE pause scoring. They wait for core to return and then re-register. This is fail-safe, not fail-open: a missing brain locks the organism down rather than letting organs act blind.

---

## 7.9 DEGRADED behavior — per module

A DEGRADED module does not behave uniformly; behavior is defined per module by its criticality:

- **Security-critical modules fail closed.** A DEGRADED VAULT refuses operations and returns `-31005 fail-closed` rather than risk an unsafe unlock. A DEGRADED TETHER holds rather than mis-escalates.
- **Advisory modules serve best-effort.** A DEGRADED ORACLE (e.g. slow Ollama) still answers as well as it can — partial reasoning beats none for an advisory signal. A DEGRADED PULSE continues scoring on the signals it still has.
- Each module spec states its own DEGRADED policy. The default for an unspecified module is fail-closed (the safe default).

---

## 7.10 Supervisor — who starts core?

Core is launched and watched by macOS launchd, using **privilege separation**:

- A thin **privileged supervisor shim** (LaunchDaemon, root) exists only to perform the few actions that genuinely require elevation — triggering PURGE's privileged steps, locking the screen at the login window, evicting Keychain items. It is intentionally small to minimize the root attack surface.
- The **main core** runs user-level (LaunchAgent), holding the router, broker, registry, and token issuer. The bulk of logic is unprivileged.
- launchd restarts core if core itself dies. This answers §6.2's "core is a single point of failure": launchd watches core, core watches modules, and the privileged shim is kept as small as possible.

The exact split of which operations cross into the privileged shim is refined in §8 (security model) and during implementation.

---

## 7.11 Open questions

- Heartbeat default 10s: confirmed adequate for liveness, but should some modules (TETHER) get a shorter liveness interval, or is the internal-tick/liveness split (§7.4) sufficient?
- `MAX_RESTARTS` window is a rolling hour — confirm this is right versus per-session.
- Core crash while a vault is unlocked: §7.8 chooses immediate relock. Confirm no grace window is ever acceptable (decision: no grace).
- Partial startup: if Wave 1 fails, do Wave 0 modules keep running standalone, or does core refuse to operate in a partial state? (Leaning: Wave 0 continues, dependents stay UNREGISTERED, operator is notified.)
- Privileged shim scope: exact list of operations that require root, finalized in §8.
- Login-window operation: which modules (if any) must function before user login, and does that force more into the LaunchDaemon?

To be resolved during implementation.

---

## 7.12 Status

**Specification.** Part 4 of 5. Depends on §6 IPC (complete).

After §8 (security model) lands, the specification phase is complete and the first code — the core skeleton (socket server, router, broker, registry, token issuer, supervisor shim) — can begin, targeted at chimera v0.2.0.

No imitations. No stubs. (See MANIFESTO §4.)

---

# §8 Security Model

> Part 5 of 5 — the final architecture document.
> Synthesizes the security posture declared per-module in §5 with the wire/auth/lifecycle layers added in §6–§7.

---

## 8.1 Purpose

Single source of truth for CHIMERA's security posture. Module specs (§5) each declared their own threats; §6 added wire-level security and capability tokens; §7 added lifecycle and privilege separation. §8 unifies them: one threat catalog, one attack surface map, one set of trust boundaries, one privilege model, and one honest list of what is NOT covered.

Where this section disagrees with a module spec, this section is authoritative. Module specs are local views; §8 is the system view.

A companion document, `chimera/docs/OPSEC.md`, addresses operator-side discipline. That file is a living artifact and is intentionally NOT part of ARCHITECTURE — it can evolve without amending the architecture.

---

## 8.2 Threat actors

CHIMERA models against nine actor classes. The last one is explicitly out of scope (§8.3).

| ID | Actor                                  | Capabilities                                                  |
|----|----------------------------------------|---------------------------------------------------------------|
| T1 | Passive network observer               | ISP, state-level masscol; sees encrypted patterns, DNS, timing; cannot decrypt TLS |
| T2 | Active network adversary               | MitM, hostile WiFi; can intercept, inject, downgrade          |
| T3 | Ad / tracking network                  | Commercial fingerprinting via mouse, keystroke, browser, cross-site |
| T4 | Local unprivileged process             | Same user, no root; can read what the user can read           |
| T5 | Local privileged process               | Has root, but not Secure Enclave or Apple Silicon ROM         |
| T6 | Physical attacker, brief access        | Minutes alone with the machine; cannot disassemble            |
| T7 | Physical attacker, seizure             | Full possession; can image disk, attempt cold-boot            |
| T8 | Coerced operator                       | Adversary can compel the operator to type passwords           |
| T9 | Nation-state / hardware extraction     | Can attack Secure Enclave, baseband, supply chain. **OUT OF SCOPE.** |

---

## 8.3 Honest scope — T9 is out of scope

CHIMERA explicitly does NOT defend against T9. We make no claim to protect against:

- Secure Enclave hardware extraction
- Baseband processor compromise
- Supply chain attacks on Apple Silicon or macOS
- Targeted zero-day exploitation by a nation-state-class adversary

This is not a weakness statement — it is a precision statement. CHIMERA is a power tool for a deliberate operator, and the operator must know the precise boundary of its guarantees. Everything below T9 is defended; T9 itself is not. No security theater (MANIFESTO §4).

---

## 8.4 Trust boundaries

CHIMERA's trust model is concentric — inward is more trusted. A boundary crossing requires an explicit authorization step.

```
[ OUTSIDE WORLD ]                            ← T1, T2, T3 live here
       ──────────
[ NETWORK STACK ]                            ← TLS, Tor, DoH at the edge
       ──────────
[ macOS USERSPACE, other apps ]              ← T4 lives here
       ──────────
[ CHIMERA modules ]                          ← scoped capability tokens (§6.9)
       ──────────
[ CHIMERA CORE ]                             ← router, broker, registry
       ──────────
[ PRIVILEGED SHIM ]                          ← thin root, only critical ops (§8.8)
       ──────────
[ macOS KERNEL / SIP ]                       ← T5 mostly stops here
       ──────────
[ SECURE ENCLAVE / APPLE ROM ]               ← T9 only
```

Three architectural rules enforce these boundaries:

1. Modules never talk to each other directly (§6.2 star topology).
2. No module touches root capabilities — only the privileged shim does, and only for the enumerated list in §8.8.
3. Capability tokens issued at connection time cannot be elevated mid-session (§6.9, §8.5 / I6).

---

## 8.5 Per-actor coverage

For each threat actor, which modules or boundaries defend, and what residual risk remains:

| Actor | Defended by                                                           | Residual risk                                       |
|-------|------------------------------------------------------------------------|-----------------------------------------------------|
| T1    | CHAFF, ECHO + TLS / Tor (network shaping)                             | Traffic-analysis with a massive corpus              |
| T2    | TLS + pinning + DoH (Cloudflared)                                      | State-issued CA in the certificate chain            |
| T3    | MIRROR + browser hardening (Tor Browser persona)                       | Server-side ML over weeks of sessions               |
| T4    | UNIX socket mode 0600 + capability tokens (§6.9)                       | Same-user info-stealing of plain (non-CHIMERA) files|
| T5    | SIP + privilege separation (§7.10) + small shim (§8.8)                 | If root is achieved, defense is very limited        |
| T6    | TETHER + screen lock + VAULT relock                                    | Physical taps, hardware implants                    |
| T7    | FileVault + VAULT crypto-shred-ready + PURGE                           | Cold-boot if seized while running                   |
| T8    | VAULT time-locks + reboot-required policies                            | Long-patience coercion, $5 wrench                   |
| T9    | (out of scope)                                                         | No defense claimed                                  |

---

## 8.6 Security invariants

System-wide rules that hold across all modules. Any future module must respect them. These are non-negotiable.

| ID  | Invariant                                                                                                                                                                                                                  |
|-----|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| I1  | **Core is the only hub.** Modules never talk to each other directly. All cross-module signal is relayed by core (§6.2).                                                                                                    |
| I2  | **No outbound network from any module except CHAFF.** Every other module makes zero outbound calls. Checked at code review and at runtime.                                                                                 |
| I3  | **Security state fails CLOSED; the operator-autonomy layer fails OPEN.** When *secrecy/safety* state is uncertain (dependency dead, core crashed, policy module offline), CHIMERA locks down — relock vaults, pause traffic, hold state (§7.6, §7.8). The ONE deliberate exception is the **operator-autonomy layer** — PULSE cognitive load + the §4 cognitive gate (§5.5): a broken or uncertain *cognitive* signal fails OPEN (mode → `normal`, gate → `allow`, override always available), because a fatigue sensor must never lock the operator out of their own machine. Secrecy fails closed to protect data; autonomy fails open to protect the operator. (Implemented: `core/gate.py` decide() defaults to allow on unknown mode; PULSE baseline/scoring default to `normal`.) |
| I4  | **Cascade can only lock more, never destroy.** A dependency failure may relock vaults, pause traffic, hold state. It can NEVER auto-trigger PURGE or any irreversible action (§7.6).                                       |
| I5  | **Privilege separation.** The main core is unprivileged (LaunchAgent). Only the minimal shim (LaunchDaemon) has root, and only for §8.8's enumerated operations.                                                           |
| I6  | **Capability scope is never expanded at runtime.** A module's capability token is issued at connect time and is immutable for the connection's life (§6.9). No method exists to "elevate" a token mid-session.            |
| I7  | **No recovery paths by design.** Forgotten master phrases are NOT recoverable. There is no escrow, no backdoor, no support flow. Operator owns the consequence (MANIFESTO §1, §5.6 VAULT).                                |
| I8  | **All destructive actions require explicit arming.** `purge.trigger` and TETHER L3 are both default-DISABLED. Arming requires a confirmation phrase AND a mandatory dry-run (§5.7, §5.8).                                  |
| I9  | **Audit trails before they matter.** Every security-relevant decision (gates, denials, escalations, purges) is logged BEFORE it executes. The log itself may be destroyed by PURGE, but never AFTER the action without record. |
| I10 | **No telemetry. No cloud. No phone-home.** CHIMERA never reports anything outside the machine. Updates are operator-driven `git pull`, not auto-update services.                                                           |

---

## 8.7 Attack surface

What an adversary can touch:

### External (network-facing)
- CHAFF outbound HTTPS (intentional, its job)
- Cloudflared DoH (system DNS)
- Anything the user opens (browser, mail) — not CHIMERA's surface
- **Nothing else from CHIMERA reaches the network**

### Local (same-machine processes)
- Two UNIX sockets in `~/.config/chimera/run/` (mode 0600)
- Module binaries on disk (each can be reverse-engineered — source is open)
- Encrypted module state files (names visible, contents protected)
- macOS Keychain entries (system-protected, Secure Enclave-backed)

### Physical
- Bluetooth LE advertising from companion (TETHER pairing window)
- The screen (anyone present can see)
- Power port (sleep / cold-boot triggers)
- The operator's keyboard (MIRROR and PULSE cannot defend against a shoulder-surfer)

---

## 8.8 Privileged shim — minimal enumerated capabilities

The root LaunchDaemon shim (§7.10) does ONLY these operations, and refuses anything else. This list IS the security boundary into root.

| # | Capability                              | Triggered by                                          |
|---|-----------------------------------------|-------------------------------------------------------|
| a | Lock the screen / activate screensaver  | TETHER L1, operator command                           |
| b | Evict CHIMERA Keychain items            | PURGE Tier 0                                          |
| c | Force-reboot                            | PURGE post-action (per config)                        |
| d | Force-killall on graceful-shutdown timeout | Core during §7.7 shutdown                          |

The shim never:
- reads file content
- opens network sockets
- executes operator-provided code
- accepts commands from anything other than the user-level core, authenticated via a per-boot shared secret

**Any addition to this list requires a formal §8 amendment, not a code change.** This is not bureaucracy; it is the architectural gate on root surface. Every root capability must pass through deliberate review.

### 8.8.1 §8 amendments to the root surface

| Amendment | Adds | Component | Status |
|-----------|------|-----------|--------|
| **A1** | ECHO constant-rate packet-shaping (pf anchor + BPF/raw-socket pacing) | a SEPARATE `chimera-echo-shaper` root LaunchDaemon — NOT the shim | **LOCKED** (Day 21) |

A1 leaves the shim's invariants untouched (it still never opens sockets); the shaper is a distinct, narrow, **fail-OPEN**, **opt-in** domain with its own enumerated capability + never-list (EP-1…8). Full review + threat analysis: `docs/ECHO_PACKET.md`.

---

## 8.9 Cryptographic primitives & key hierarchy

### Primitives

- **Symmetric AEAD:** AES-256-GCM via libsodium
- **KDF:** Argon2id (memory-hard) for any operator-phrase derivation
- **Hash:** BLAKE2b-256 for integrity and policy-hash binding
- **Random:** hardware RNG (`mrs RNDR` on AArch64) seeding ChaCha20 PRNG (CHAFF/MIRROR)
- **Asymmetric:** NOT USED locally — no PKI, no identity infrastructure

### Key hierarchy (top is most protected)

1. **macOS Secure Enclave** — non-extractable per-vault master keys, TETHER IRK
2. **Operator master phrase** — never stored; derives Argon2id keys
3. **Per-connection capability tokens** — ephemeral, in-memory only
4. **Module on-disk state keys** — derived per-module, encrypted at rest

Keys NEVER cross trust boundaries. The Secure Enclave never exposes raw key material; signing and decryption happen inside the Enclave.

---

## 8.10 Audit log policy

Audit logs are configurable, with conservative defaults.

- **Default:** encrypted on-disk under a VAULT-class key, retention 30 days, automatic rotation
- **What is logged:** every gate decision, denial, escalation, capability-token issuance, PURGE arm/disarm, TETHER L3 arm/disarm
- **What is NEVER logged:** file contents, raw policy variable values (current SSID, exact PULSE score), keystroke or mouse content, vault contents
- **PURGE Tier 0** destroys logs along with keys — by design, the operator can always erase their forensic trail when they choose
- **Operator-tunable:** can be set to in-memory-only (max deniability) or extended retention (max accountability) via core config

The defaults balance operator self-forensics with deniability under coercion (T8).

---

## 8.11 Update model

CHIMERA updates are operator-driven, never automatic. The update mechanism is a `git pull` from the operator's chosen remote — auditable, transparent, and preserves invariant I10 (no telemetry, no phone-home).

This is intentionally slow for security fixes. A signed-update channel would be faster but would require a phone-home component, violating I10. The trade-off is deliberate: CHIMERA is a power tool for an operator who pulls fixes deliberately, not a consumer product with auto-update.

Future work may introduce a signed manifest on GitHub that the operator can verify before pulling, but no networked update agent will ever live inside CHIMERA.

---

## 8.12 Open questions

- **DoH trust:** Cloudflared is the default DoH provider (T2 mitigation). What if Cloudflare itself is compromised or compelled? The architecture allows swapping providers, but the trust assumption remains.
- **BLE identity leak:** TETHER's BLE advertising is observable to nearby radios — "this machine pairs with phone X" is itself a fingerprint. Is the leak acceptable, or does it warrant an obfuscation layer?
- **Audit depth presets:** beyond default / in-memory / extended, are there other useful retention profiles (e.g. ephemeral 24h, paranoid 7d)?
- **Threat-model review cadence:** when is §8 itself re-reviewed? Yearly? On each new module? On any invariant change?
- **OPSEC.md scope:** a separate file is planned (decision: appendix-as-file). What is its minimum content for v1? At least: persona separation, override-phrase hygiene, panic-gesture practice.
- **Cold-boot residue measurement:** §8.5 lists cold-boot as a residual risk for T7. Should CHIMERA include an opt-in "panic suspend" path that aggressively zeroes RAM regions before suspend?

To be resolved during implementation and during OPSEC.md authoring.

---

## 8.13 Status

**Specification.** Part 5 of 5 — the final architecture document.

With §8 in place, **the specification phase is complete**. The architectural document is whole: §1–§4 (concept, stack, principles), §5 (eight module specifications), §6 (IPC protocol), §7 (lifecycle), §8 (security model).

Next is code: the core skeleton — socket server, router, broker, registry, capability-token issuer, and the privileged shim — targeted at chimera v0.2.0. Specifications anchor the code; the code does not re-litigate the specifications.

The companion document `chimera/docs/OPSEC.md` — operator-side discipline — is the next non-code artifact, written before or alongside the first code.

No imitations. No stubs. (See MANIFESTO §4.)
