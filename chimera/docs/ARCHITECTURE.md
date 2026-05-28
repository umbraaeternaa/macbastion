# CHIMERA — Architecture (Part 1 of 5)

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

**Status:** Part 1 (§1–§4) and Part 3 (§6) complete. Next: §5.7–§5.8 module specs, then §7 lifecycle, §8 security model.

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
