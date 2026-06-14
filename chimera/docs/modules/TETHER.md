# §5.7 TETHER — Proximity Dead-Man Switch

Module: `tether`
Codename origin: Tether — the line that keeps you connected; when it breaks, something must happen
Status: **Planned** (seventh CHIMERA module, second event-driven defense, first C++ module)
Target version: chimera v0.8.0
Estimated effort: 5-6 working sessions (~22 hours)

---

## 1. Mission

Pairs CHIMERA with a trusted companion device (the operator's phone) over Bluetooth LE and continuously measures presence. When the companion moves out of range for longer than a grace period, TETHER fires an escalating, time-gated response: lock screen, then lock CHIMERA vaults, then — only if explicitly armed — trigger PURGE.

The premise: if the operator is forcibly separated from the machine, or simply walks away in a hostile or shared space, the machine should not remain open and undefended. The companion device is the operator's continued presence, expressed as a radio signal.

TETHER is the second event-driven module and the first written in C++ (justified by CoreBluetooth, an Objective-C framework). It is also the only module capable of destroying data, via its opt-in L3 tier — so its safety model (§8) is the strictest in CHIMERA.

---

## 2. Why unique

Existing approaches to "defend the machine when I'm not near it" each solve only part of the problem:

- **Device tracking** (Find My, Tile): tells you WHERE a lost device is after the fact. It does not DEFEND the device at the moment of separation.
- **Proximity unlock** (Apple Watch unlocking a Mac): unlocks on approach, but on departure does nothing protective beyond the eventual idle screen lock minutes later.
- **USB dead-man switches** (BusKill): a physical cable tethers the operator to the desk; pulling the cable triggers a lockdown. Effective, but it physically chains you to the machine.

TETHER differs by combining three properties no existing tool has together:

1. **Wireless, not physical.** No cable. The operator moves freely; presence is measured by radio.
2. **Escalating, not binary.** Not just "locked / unlocked" — a graded ladder (screen, vaults, purge) with grace windows and cancellation at every reversible stage.
3. **Organ-integrated.** TETHER does not act alone; it drives CHIMERA's other organs through core — locking VAULT, optionally triggering PURGE — rather than reimplementing each defense itself.

This is the first wireless proximity dead-man switch on macOS that escalates through a coordinated security organism.

---

## 3. Algorithm

### Pairing (one-time)

  - Operator enters pairing mode (tether.pair.start)
  - BLE bond established with companion + out-of-band secret exchange
  - TETHER stores the companion's Identity Resolving Key (IRK) so it can
    recognize the phone even as its BLE MAC rotates for privacy (modern
    iOS/Android rotate the advertised address every ~15 min)
  - IRK stored in macOS Keychain (Secure Enclave protected), same trust
    tier as VAULT's master secret

### Continuous monitoring (steady state)

  every TICK (default 2s):
    scan BLE, resolve companion via IRK
    measure RSSI (signal strength)
    smooth with EWMA (alpha 0.3) to reject momentary spikes
    update presence state machine:

  PRESENT  — smoothed RSSI above near_threshold, seen within last tick
  FRINGE   — RSSI weak, OR 1-2 ticks missed (uncertain, no escalation yet)
  ABSENT   — N consecutive ticks missed (default 5 ≈ 10s)

### Disappearance classification (anti-weaponization)

When the companion stops being seen, TETHER classifies HOW it vanished:

  FADE        — RSSI declined gradually over several ticks before loss.
                Consistent with the operator walking away. → normal escalation.
  CLEAN_DROP  — companion sent a clean BLE disconnect (e.g. Bluetooth turned
                off, battery low shutdown). → treat as benign, alert only.
  INSTANT_DROP— signal was strong, then vanished within one tick with no
                fade and no clean disconnect. → SUSPICIOUS (possible jamming).
                DELAY escalation, raise alert, do NOT accelerate.

This classification is what makes the destructive L3 tier defensible: a jammer
that kills the signal instantly slows TETHER down, it does not speed it up.

### Escalation ladder (on confirmed ABSENT via FADE, time-gated)

  T+0s       ABSENT confirmed → emit tether.absent, start grace timer
  T+grace    (default 30s) still absent → L1: lock screen
  T+L2       (default +60s) still absent → L2: lock ALL CHIMERA vaults
  T+L3       (default +300s, OPT-IN ONLY, default DISABLED) still absent →
             L3: trigger PURGE

### Recovery (companion returns before L3)

  smoothed RSSI back above near_threshold for M ticks (default 3):
    CANCEL any pending escalation
    emit tether.recovered {at_stage}
    reset to PRESENT
  L1 and L2 effects are reversible — the operator re-authenticates and
  unlocks. L3 is NOT reversible. There is no recovery from PURGE.

---

## 4. Why C++ (the only C++ module)

CHIMERA's stack is Python + C + ARM64 Asm by default. TETHER is the single exception, for one reason:

- BLE on macOS is **CoreBluetooth**, an Objective-C framework. C++ with Objective-C++ (`.mm` files) bridges to it cleanly; pure C would require hand-written Objective-C runtime messaging, which is uglier and more error-prone than the binding it replaces.
- The presence state machine, EWMA smoothing, and multi-stage escalation timers benefit from RAII (deterministic cleanup of BLE scan handles and timers) and `std::chrono` (precise, type-safe time math) without a garbage collector.

C++17 is therefore justified here and only here. No other module should adopt it.

---

## 5. Stack

| Component         | Tech                                  | Reason                                              |
|-------------------|---------------------------------------|-----------------------------------------------------|
| Core daemon       | C++17                                 | State machine, timers, RAII over BLE handles        |
| BLE binding       | Objective-C++ (`.mm`) + CoreBluetooth | Only stable BLE central API on macOS                |
| Identity          | IRK in macOS Keychain (Secure Enclave)| Resolve rotating companion MAC; theft-resistant     |
| Smoothing/timers  | `std::chrono`, EWMA in plain C++      | Type-safe time, no GC                               |
| IPC with core     | UNIX socket + JSON-RPC 2.0 (per §6)   | Star topology; escalations are core-enforced        |
| Watches/timers    | kqueue (EVFILT_TIMER)                 | Escalation stage timers, event-driven              |
| Build system      | clang++ -std=c++17 -Wall -Wextra      | Objective-C++ needs clang; Makefile like CHAFF      |

**Companion side** (the phone) is out of scope for this module. It is either the phone's existing BLE identity or a small signed-beacon app — a separate artifact, specified later if needed.

### Demo — a reproducible companion beacon

The companion only has to do ONE thing: **advertise a fixed BLE service UUID**. macOS hides
device MACs, so TETHER matches on that advertised service UUID, not a hardware address — set
`companion_id` (in TETHER's `config.json`) to the UUID your beacon broadcasts. CHIMERA's example
UUID spells the project: `6368696D-6572-6100-0000-000000000001` (`chimera` in ASCII).

Pick any reliable advertiser (steadiest first):

1. **CHIMERA's built-in `companion-beacon`** (recommended — turnkey, in-repo): build it once with
   `make -C modules/tether companion`, then run `./modules/tether/companion-beacon` on the Apple
   device you carry (a spare Mac / iPad / an iPhone via Xcode). With no args it advertises the
   default project UUID — so it matches TETHER out of the box; first run prompts for the Bluetooth
   grant. Override with `companion-beacon <service-uuid> <local-name>`.
2. **A configurable BLE tag** (nRF52 / a generic iBeacon dev-tag) set to advertise the service
   UUID — hands-free, most reliable for an unattended, pocketable dead-man.
3. **A phone advertiser app** broadcasting that UUID (nRF Connect works but advertises flakily).

Then:

1. Put it in TETHER's config: `{"companion_id": "6368696D-6572-6100-0000-000000000001"}`.
2. Confirm TETHER hears it: `tether.status` → a non-zero `rssi_smoothed` and a `NEAR`/present
   `state` mean the scanner is locked on. No RSSI ⇒ the advertiser isn't broadcasting that UUID
   (or the TETHER binary lacks Bluetooth permission).
3. Run the dead-man: with the beacon present, carry it out of range. After the grace period
   TETHER emits `tether.escalation` and **core** actuates the ladder — L1 lock screen (shim),
   L2 lock the vault — and, **only if you ran `tether.l3.arm`**, L3 PURGE. Bring it back before
   L3 → `tether.recovered` → the posture stands down (the vault stays locked — re-open is always
   deliberate).

Honest limits (§4): the beacon must advertise *continuously* (a sleeping phone radio = apparent
absence = a false dead-man trip); and TETHER claims presence only for the exact configured UUID
(an unset `companion_id` never matches — no companion, no presence).

**Escalation actions are core-enforced, not TETHER-enforced.** TETHER only detects absence and emits `tether.escalation` events. Core is what actually calls `vault.lock` (L2) and `purge.trigger` (L3). This keeps the destructive capability auditable in one place (core) and means disabling TETHER cannot leave a half-armed dead-man behind.

---

## 6. IPC API (per §6 envelope)

### Commands (core → tether)

| Method                      | Params                                              | Returns                                                  |
|-----------------------------|-----------------------------------------------------|----------------------------------------------------------|
| `tether.status`             | none                                                | `{state, rssi_smoothed, companion_paired, escalation_stage, l3_armed}` |
| `tether.pair.start`         | none                                                | `{pairing_challenge}` — enter pairing mode               |
| `tether.pair.confirm`       | `{oob_secret}`                                      | `{ok, companion_id}`                                     |
| `tether.unpair`             | `{confirm}`                                         | `{ok}`                                                   |
| `tether.config.set`         | `{tick, grace, l1_delay, l2_delay, near_threshold, ...}` | `{config}`                                          |
| `tether.l3.arm`             | `{confirmation_phrase}`                             | `{ok, l3_armed: true}` — enable destructive tier         |
| `tether.l3.disarm`          | none                                                | `{ok, l3_armed: false}`                                  |
| `tether.escalation.cancel`  | none                                                | `{ok, cancelled_stage}` — manual operator override       |
| `tether.test`               | `{stages}`                                          | `{dry_run_report}` — simulate ladder, take NO real action|

### Events (tether → core; core relays per §6.6)

| Event                       | Payload                                                            |
|-----------------------------|--------------------------------------------------------------------|
| `tether.present`            | `{rssi_smoothed}`                                                  |
| `tether.fringe`             | `{rssi_smoothed, ticks_missed}`                                    |
| `tether.absent`            | `{since_ts, last_rssi, disappearance_class}`                       |
| `tether.escalation`         | `{stage: L1\|L2\|L3, action_requested, grace_remaining}`           |
| `tether.recovered`          | `{at_stage, rssi_smoothed}`                                        |
| `tether.suspicious`         | `{reason: instant_drop, escalation_delayed_by_sec}`                |
| `tether.companion.lost`     | `{reason: unpaired\|bond_broken}`                                  |
| `tether.error`              | `{code, message, recoverable: bool}`                               |

---

## 7. Dependencies

System:
- macOS 14+, Bluetooth LE hardware (built-in on all Apple Silicon)
- Bluetooth permission (TCC: `NSBluetoothAlwaysUsageDescription`)
- CoreBluetooth.framework (system-shipped)
- A companion device with BLE (the operator's phone)
- ~4 MB binary, ~15 MB RAM, modest BLE-scan power cost

CHIMERA integrations:
- **core** (mandatory) — escalation L1/L2/L3 are core-enforced actions
- **VAULT** (for L2) — TETHER emits, core calls `vault.lock` on all vaults
- **PURGE** (for L3, opt-in) — TETHER emits, core calls `purge.trigger`
- **PULSE** (optional, future) — presence could feed PULSE as a signal (deferred)

Project-internal:
- IRK + companion bond in macOS Keychain (label `chimera-tether-companion`)
- `~/.config/chimera/tether/config.json` — timings, thresholds, l3_armed flag
- IPC socket via core (no direct sockets)

Network: TETHER makes NO outbound network calls. Bluetooth-only, local module.

---

## 8. Security & safety model

This module can lock the operator's screen, lock their vaults, and — when armed — destroy their data. Its safety model is therefore the strictest in CHIMERA.

### Protects against
- Forced separation: operator dragged from the desk with phone on their person → machine defends itself as the operator (and phone) recede
- Walk-away in a hostile or shared space: operator steps away and forgets to lock; TETHER locks for them
- Evil-maid window: a machine left briefly unattended locks down once the operator's presence fades

### Explicitly does NOT protect against (honest scope)
- **Snatch-and-run.** If the adversary grabs the MACHINE and the operator (with the phone) stays behind, the phone is still present, so TETHER does not fire. This is by design: TETHER's anchor is the phone (decision: anchor model C). Snatch-and-run is covered by screen lock + FileVault, not by TETHER. TETHER does not claim to defend it.
- Adversary who seizes BOTH machine and phone together
- Relay/amplification attacks that artificially extend BLE range to keep the companion appearing PRESENT
- A jammer combined with a 5+ minute wait IF L3 is armed (mitigated, not eliminated — see below)

### Safety invariants (CRITICAL — L3 can destroy data)
- **L3 is opt-in only, default DISABLED.** PURGE is never triggered automatically unless the operator explicitly ran `tether.l3.arm` with a confirmation phrase.
- **Mandatory test mode before arming.** `tether.test` performs dry-runs of the full ladder, taking NO real action, so the operator sees the state machine behave before the destructive tier is ever enabled.
- **Every reversible stage has a grace window and a cancel.** L1 (screen) and L2 (vaults) are fully reversible by re-authentication. Only L3 is irreversible.
- **Jamming slows escalation, never speeds it.** An INSTANT_DROP (signal vanishing within one tick with no fade and no clean disconnect) is classified suspicious: escalation is DELAYED and an alert raised. A jammer cannot accelerate the ladder toward PURGE — it can only stall it.
- **Clean disconnect is benign.** A phone turning Bluetooth off or dying on low battery sends a clean BLE disconnect; this is treated as alert-only, never as the FADE pattern that drives escalation.

### Residual risk (stated plainly)
Even with every invariant above, an operator who arms L3 and then leaves their phone behind for longer than grace + L1 + L2 + L3 (default ~6.5 min) risks data loss. Conservative defaults and mandatory test mode minimize this; they do not make it zero. Arming L3 is a deliberate choice for a specific threat model (data must not fall into hostile hands), and the operator owns that choice (MANIFESTO §1).

### Threat model assumptions
- Adversary cannot extract the IRK from Secure Enclave
- Adversary cannot inject IPC into core (capability tokens, §6.9)
- The operator keeps the companion device on their person when L3 is armed
- BLE jamming, if it occurs, is detectable as INSTANT_DROP often enough to delay rather than trigger L3

---

## 9. Open questions

These need decisions before implementation begins:

- **Jamming heuristic calibration.** INSTANT_DROP vs FADE is the linchpin of L3 safety, but elevators, Faraday environments, and signal nulls also produce instant drops. How aggressively to delay on suspicion? What false-positive rate on "suspicious" is acceptable?
- **Quorum companions (v2).** Phone AND watch, both must be absent (2-of-2) before escalation — dramatically fewer false positives, but requires two devices and more state. Deferred from v1, but should the data model anticipate it now?
- **Grace/threshold calibration process.** What is the recommended procedure for an operator to tune `near_threshold`, `grace`, and the L-delays to their environment before relying on TETHER? A guided `tether.test` walkthrough?
- **PULSE integration.** Should presence feed PULSE (e.g. operator present + tired → different gating)? Or keep the modules independent to avoid coupling?
- **L3 multi-condition gating.** Should L3 ever require a corroborating signal beyond BLE absence (e.g. also a specific time window, or PULSE state) to fire? Stronger anti-weaponization, but risks the corroborating signal not arriving in a real emergency.
- **BLE scan power profile.** Continuous 2s scanning vs adaptive (slower scan when recently PRESENT, faster when FRINGE). Battery impact measurement needed.

To be resolved during implementation.

---

## 10. Status

**Planned.** No code yet.

Depends on:
- Core orchestrator with IPC infrastructure (§6, now complete)
- VAULT (for L2 escalation target)
- PURGE (for L3 escalation target — and L3 is opt-in, default off)
- macOS Bluetooth permission flow from core

After TETHER, only PURGE (§5.8) remains to complete the module specifications (Part 2). PURGE is also the L3 target TETHER depends on, so PURGE must be specified before either module's code is written. With TETHER specified, the event-driven layer (VAULT, TETHER, PURGE) is two-thirds defined.

No imitations. No stubs. (See MANIFESTO §4.)
