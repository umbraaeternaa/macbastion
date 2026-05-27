# §5.5 PULSE — Cognitive Load Monitor

Module: `pulse`
Codename origin: Pulse — the body's signal that something is straining; PULSE listens to the same kind of signal in the operator's interaction patterns
Status: **Planned** (fifth CHIMERA module, first cognitive-state defense)
Target version: chimera v0.6.0
Estimated effort: 4-5 working sessions (~18 hours)

---

## 1. Mission

Passive sensor that estimates the owner's cognitive load from input patterns (typing rate, error rate, mouse jitter, idle gaps, time of day) and raises friction on destructive actions when load exceeds threshold.

PULSE does NOT diagnose, treat, monitor health, or report to anyone. It treats the owner as a system whose error rate spikes under fatigue — and inserts speed bumps before irreversible operations in those moments. When the operator is rested and focused, PULSE is invisible. When the operator is at 3am after 14 hours of work, PULSE asks once more.

This is the only CHIMERA module that observes the operator rather than the system or the outside world. Its design therefore carries explicit autonomy and privacy invariants (see §8).

---

## 2. Why unique

Existing tools that touch this space fall into three categories, none sufficient:

- **Static OS confirmations** (`Are you sure?`, `Move to Trash?` dialogs): identical whether the user is rested or impaired. Pure ceremony, easily clicked through.
- **Cloud-based wellness platforms** (Apple Health, Oura, Whoop, RescueTime): track sleep, HRV, and focus minutes — but never gate actions in real time, and stream personal state data to vendor servers.
- **Productivity timers** (Toggl, Be Focused, Pomodoro apps): measure focus AFTER the fact. They cannot prevent a tired user from deleting the wrong folder at 3am.

PULSE differs by combining four properties no existing tool has together:

1. **OS-level gating, not after-the-fact tracking.** Cognitive state changes WHAT the system allows, in real time.
2. **Local-only signal extraction.** Derived from MIRROR's aggregate counters; raw input never leaves the kernel, let alone the machine.
3. **Autonomy-preserving.** Every gate has an override path. PULSE is a speed bump, never a cage.
4. **Action-scoped, not session-scoped.** Doesn't lock the whole machine; gates only actions explicitly registered as "danger" by the operator.

This is the first OS-level cognitive-load gate on macOS, open-source or otherwise.

---

## 3. Algorithm

PULSE produces a single rolling `fatigue_score` in `[0.0, 1.0]`, updated every 60 seconds, derived from three signal groups.

### Signal group A — Input patterns (from MIRROR)

PULSE subscribes to MIRROR's aggregate counters (never raw events). Per minute, MIRROR exposes:
  - characters typed
  - backspaces / deletes
  - mouse path length vs straight-line distance ratio
  - average keystroke flight time

PULSE compares each to the operator's 14-day rolling baseline:
  - typing speed delta (slower than baseline → fatigue indicator)
  - error rate delta (more deletes per char → fatigue indicator)
  - mouse inefficiency delta (longer paths for same target → fatigue indicator)

### Signal group B — Temporal context

  - hour of day, weighted by personal chronotype baseline
    (3am is +0.3 for a typical operator, but only +0.05 for one whose
     baseline shows regular night work)
  - hours since last meaningful idle gap (>15 min continuous idle)
  - total session duration since last reboot or long idle

### Signal group C — Behavioral drift (optional)

If ORACLE is running, PULSE consumes `oracle.anomaly.detected` events. If ORACLE flags behavior as anomalous AND its severity delta exceeds 0.3 within the same 5-minute window, PULSE factors that in.

### Scoring

  fatigue_score = w_a * input_delta + w_b * temporal + w_c * drift

  default weights: w_a=0.55, w_b=0.30, w_c=0.15

  weights configurable via IPC; sum must equal 1.0

  baseline is the operator's "calm Tuesday afternoon": the 14-day rolling
  median of all signals, computed only over sessions where no `pulse.danger.gated`
  event fired (to avoid feedback loops).

History is stored in encrypted SQLite (Fernet/AES-128) with a 7-day rolling window. Older buckets are purged automatically. **No raw input content is ever stored** — only aggregates and the resulting score.

---

## 4. Friction levels

The score maps to four modes, each with explicit, predictable behavior on registered danger actions:

| Score      | Mode      | Effect on danger actions                                         |
|------------|-----------|------------------------------------------------------------------|
| 0.0 – 0.4  | normal    | no intervention — actions proceed as if PULSE were off           |
| 0.4 – 0.7  | caution   | +1 extra confirmation dialog with the score visible              |
| 0.7 – 0.9  | tired     | +5s mandatory delay before action; score + reasoning shown       |
| 0.9 – 1.0  | exhausted | block by default; override phrase required (logged, never cached)|

In `exhausted` mode the override path always exists — see §8 *autonomy invariant*. PULSE cannot lock the operator out of their own machine.

### Danger registry

A "danger action" is anything explicitly listed in the registry. Default contents (operator can edit at any time):

  - `rm` / unlink operations in `$HOME` (NOT `/tmp`, NOT project workdirs)
  - PURGE trigger (any path)
  - VAULT unlock outside the scheduled window
  - Browser POST to registered financial domains (banks, brokers, crypto)
  - `git push --force` and `git push --force-with-lease` on protected branches
  - Outbound email/Slack/Signal to pinned high-stakes contacts (lawyer, partner, employer)

Non-default suggestions, off by default: shutdown/reboot, mass file moves, IDE bulk refactor commands.

The registry is intentionally short. The operator owns it.

---

## 5. Stack

| Component        | Tech                                  | Reason                                              |
|------------------|---------------------------------------|-----------------------------------------------------|
| Signal collector | C17 (small daemon)                    | Subscribes to MIRROR/ORACLE IPC, low overhead       |
| Scoring engine   | Python 3.11+ asyncio                  | Rule logic, baseline math, easier to evolve         |
| Idle detection   | kqueue (`EVFILT_TIMER` + IOKit idle)  | Event-driven, no polling                            |
| History store    | SQLite + Fernet (AES-128)             | Encrypted at rest, 7-day rolling window             |
| IPC with core    | UNIX socket + JSON-RPC 2.0            | Same protocol as CHAFF/ECHO/ORACLE/MIRROR           |
| Action gating    | Implemented in core, driven by PULSE  | PULSE only emits mode; core enforces gates          |
| Build system     | clang + pip + venv                    | Hybrid like ORACLE                                  |

**Why hybrid C + Python:** Signal collection must be lightweight and run continuously (C side). Scoring rules and weights evolve frequently; Python lets us iterate without rebuilds. The IPC boundary is the natural split.

**Why core enforces gates, not PULSE itself:** PULSE is advisory. It publishes `mode` and `score`. Core is the only component allowed to actually block actions, which keeps PULSE auditable and removable — turning PULSE off cannot leave the system in a locked state.

**Why no notifications, no menu bar widget:** PULSE is silent infrastructure. Its only user-visible surface is the gate dialog itself, when it fires. Anything more would pressure the operator about their state, which is the opposite of the goal.

---

## 6. IPC API

### Commands (core → pulse)

| Method                    | Params                              | Returns                                          |
|---------------------------|-------------------------------------|--------------------------------------------------|
| `pulse.status`            | none                                | `{score, mode, baseline_ready, session_minutes}` |
| `pulse.calibrate.start`   | none                                | `{ok, days_required: 14}`                        |
| `pulse.calibrate.reset`   | none                                | `{ok}` — discard baseline, start over            |
| `pulse.danger.add`        | `{action_signature}`                | `{registry}`                                     |
| `pulse.danger.remove`     | `{action_signature}`                | `{registry}`                                     |
| `pulse.danger.list`       | none                                | `{registry: [...]}`                              |
| `pulse.weights.set`       | `{w_a, w_b, w_c}` (sum = 1.0)       | `{config}`                                       |
| `pulse.override`          | `{phrase, action_signature}`        | `{ok, logged: true}`                             |
| `pulse.disable`           | `{confirm: true}`                   | `{ok, enabled: false}` — logged                  |
| `pulse.enable`            | none                                | `{ok, enabled: true}`                            |

### Events (pulse → core)

| Event                       | Payload                                                                |
|-----------------------------|------------------------------------------------------------------------|
| `pulse.mode.changed`        | `{old_mode, new_mode, score, primary_signal}`                          |
| `pulse.danger.gated`        | `{action_signature, mode, decision: allow|confirm|delay|block}`        |
| `pulse.override.used`       | `{action_signature, mode_at_time, phrase_hash, timestamp_utc}`         |
| `pulse.baseline.ready`      | `{calibration_days: 14, baseline_summary}` (sanitized)                 |
| `pulse.signal.degraded`     | `{missing: [mirror|oracle], fallback: temporal_only}`                  |
| `pulse.error`               | `{code, message, recoverable: bool}`                                   |

---

## 7. Dependencies

System:
- macOS 14+
- ~50 MB free disk (encrypted history + logs)
- ~30 MB RAM resident

Module dependencies:
- MIRROR running — required for input signals (group A). If MIRROR is off, PULSE emits `pulse.signal.degraded` and falls back to temporal signals only (group B). Scoring still works, just less accurately.
- ORACLE running — optional. If present, drift signal (group C) is mixed in. If absent, weights renormalize automatically (`w_a` and `w_b` rescale to sum 1.0).
- Core orchestrator with IPC and gate-enforcement logic.

Python (in chimera's venv):
- `cryptography` — Fernet encryption
- `pydantic` — event schema validation
- Standard library: `asyncio`, `sqlite3`, `json`, `statistics`, `time`

Project-internal:
- `~/.config/chimera/pulse/baseline.db` — encrypted SQLite, 7-day rolling
- `~/.config/chimera/pulse/registry.json` — danger registry (operator-editable)
- IPC socket via core (no direct sockets)

Network: PULSE makes NO outbound network calls. Pure local module.

Calibration: 14-day cold-start period. During calibration `mode` is forced to `normal` regardless of signals; PULSE records baseline silently.

---

## 8. Security & ethical model

### Protects against
- The operator's own destructive actions under fatigue, impairment, or stress
- Social-engineering attacks timed to known fatigue windows (late-night urgent emails)
- "3am panic" cascade decisions (mass deletions, account closures, irreversible sends)
- Coercion attempts (every gate event is timestamped and logged for forensics)

### Does NOT protect against
- Sober, calm, deliberate destructive actions (and intentionally does not — that's the operator's right)
- Medical emergencies (PULSE is not a health monitor and does not call anyone)
- Compromised PULSE daemon (if PULSE is compromised, threat model assumes adversary can suppress gates; mitigation: gates also flow through core, which is independently auditable)

### Privacy invariant
PULSE NEVER stores raw input content. No keystrokes, no coordinates, no event payloads. Only:
- per-minute aggregate counters (chars, deletes, mouse path ratio)
- per-day rolling baseline statistics
- gate event logs (action signature, mode, decision, timestamp)

No data leaves the machine. Ever. PULSE state is wiped by PURGE on panic-button trigger.

### Autonomy invariant
PULSE cannot lock the operator OUT.
- Every gate, in every mode, has an override path.
- The override phrase is set by the operator during initial setup and stored as a salted hash. It cannot be reset or rotated by PULSE itself, only by the operator running `pulse.override.rotate` while in `normal` mode.
- The override phrase is typed in full every time. It is never cached, never partial-matched, never bypassable by repeat-action shortcuts.
- If PULSE is somehow forced into permanent `exhausted` mode by a compromise, the operator can still disable PULSE entirely via `pulse.disable` from core — which itself requires the override phrase, but is always available.

PULSE is a speed bump, not a cage. The operator is sovereign (MANIFESTO §1).

### Threat model assumptions
- Adversary cannot read PULSE process memory (SIP enforced)
- Adversary cannot tamper with baseline DB (encrypted, integrity-checked)
- The operator chooses the override phrase wisely and remembers it
- PULSE output is treated as advisory by core; core's gate-enforcement code is the security boundary, not PULSE itself

---

## 9. Open questions

These need decisions before implementation begins:

- **Calibration window length.** 14 days is conservative but means PULSE is dormant for 2 weeks after install. Alternative: 7-day "soft" calibration where PULSE activates with wider tolerance, then narrows over the next 7 days. Trade-off: faster activation vs more false positives early on.
- **Chronotype detection.** How aggressively should PULSE adjust temporal weights to night owls vs morning people? Risk of over-adapting and never flagging genuine 3am fatigue.
- **Override phrase rotation policy.** Force rotation every N days? Allow indefinite? Trade-off between security hygiene and operator annoyance.
- **Per-action override scope.** Should an override apply to one action only, or to all danger actions for the next 60 seconds? Strict (one action) vs ergonomic (bulk).
- **Gate dialog UI.** Native macOS dialog vs terminal prompt vs SwiftBar widget. Each has different attack surfaces.
- **Integration with macOS Focus modes / Do Not Disturb.** Should Focus state be a signal (operator is intentionally focused → score reduced)? Or ignored to avoid manipulation?
- **Feedback loop avoidance.** Baseline must exclude gated sessions to prevent learning "tired is normal". Is 5-minute exclusion window enough?

To be resolved during implementation.

---

## 10. Status

**Planned.** No code yet.

Depends on:
- MIRROR being implemented (for input signal stream)
- Core orchestrator with IPC infrastructure
- Core gate-enforcement subsystem (separate from PULSE itself)
- Operator-defined override phrase (one-time setup)

After PULSE works, CHIMERA covers the five major fingerprinting and exploitation surfaces: network (CHAFF, ECHO), system reasoning (ORACLE), input layer (MIRROR), and cognitive state (PULSE). The remaining three modules (VAULT, TETHER, PURGE) shift focus from continuous defenses to event-driven safeguards.

No imitations. No stubs. (See MANIFESTO §4.)
