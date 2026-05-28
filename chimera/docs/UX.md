# CHIMERA — UX Surface Decision Record

> Decision date: 2026-05-28
> Status: **Decided** — hybrid (CLI + swiftbar + event stream)
> Affects: ARCHITECTURE §6 (IPC protocol), all module IPC tables

---

## Decision

CHIMERA is controlled through three complementary surfaces, not one:

| Surface       | Role                          | Interaction model            |
|---------------|-------------------------------|------------------------------|
| CLI           | Commands (unlock, start, config) | Synchronous request/response |
| swiftbar      | Passive state monitoring      | Polling (every N seconds)    |
| Event stream  | Critical push notifications   | Pub/sub subscription         |

This is the canonical answer to "how does the operator interact with CHIMERA".

---

## Rationale

The eight modules have fundamentally different interaction needs, and no single
surface serves all three:

1. **Complex commands need a CLI.** `vault unlock work-docs` with a policy DSL,
   `chaff start --profile medium`, `pulse danger.add` — these are deliberate,
   parameterized actions. A menu bar cannot express them cleanly.

2. **Ambient state needs passive monitoring.** "CHAFF active, PULSE caution,
   VAULT locked" is information the operator wants at a glance, without asking.
   swiftbar (already present in macbastion parent project) polls and displays.

3. **Danger needs to push, not wait.** ORACLE anomaly detection, VAULT auto-relock,
   TETHER proximity break — these cannot wait for the operator to run `status`.
   They must surface the moment they happen. This requires a push channel.

Two of the three surfaces already exist in the macbastion parent project (CLI
and swiftbar). Only the event stream is new infrastructure.

---

## Consequences for IPC (§6)

This decision constrains the IPC protocol design:

- **Request/response** is required for CLI command execution (method call → result).
- **Event subscription** is required so swiftbar can poll efficiently AND so the
  event stream can push critical events without polling.
- The protocol must therefore support BOTH a synchronous call model AND an
  asynchronous pub/sub model over the same UNIX socket + JSON-RPC 2.0 transport.
- A **core-side event broker** is mandatory: modules emit events to core, core
  fans them out to subscribers (swiftbar, event-stream listeners, and any module
  that subscribed — e.g. PULSE consuming ORACLE anomalies).

The event broker was implicitly required already (ORACLE's push events, PULSE's
consumption of ORACLE events, VAULT's condition watches all assume it). This
decision makes it explicit and central.

---

## Open questions (deferred to §6)

- Event stream transport: same UNIX socket with a subscribe method, or a
  separate dedicated socket per subscriber?
- Backpressure: what happens if a subscriber (slow swiftbar) can't keep up with
  event volume from CHAFF?
- swiftbar polling interval vs event push: does swiftbar poll state AND receive
  pushes, or only poll?
- Authentication between surfaces and core (local socket — is filesystem
  permission enough, or per-client tokens?)

---

## Status

**Decided.** No code yet. This record exists to anchor §6 IPC protocol design.

Next: ARCHITECTURE §6 — IPC protocol (envelope format, error codes, event
subscription model, capability negotiation).
