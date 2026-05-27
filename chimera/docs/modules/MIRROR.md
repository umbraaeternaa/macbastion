# §5.4 MIRROR — Behavioral Noise Injector

Module: `mirror`
Codename origin: Mirror — reflects user's intent back to the system, but with a slight distortion that breaks pattern recognition
Status: **Planned** (fourth CHIMERA module, first input-layer defense)
Target version: chimera v0.5.0
Estimated effort: 4-5 working sessions (~16 hours)

---

## 1. Mission

System-level event tap that adds humanlike jitter to mouse, keyboard, and scroll events at the OS layer — defeats behavioral biometrics (mouse curves, keystroke dynamics, dwell/flight timing) used by reCAPTCHA v3, fingerprint.js, ad networks, and bank fraud-detection systems.

MIRROR sits between the kernel and userspace applications. Every input event passes through it before reaching the foreground app. It modifies — never logs — the event payload, breaking the statistical signature that behavioral fingerprinters depend on.

Where CHAFF/ECHO defend the network layer and ORACLE observes system behavior, MIRROR defends the human-machine interface itself — the layer most trackers assume is unobservable and immutable.

---

## 2. Why unique

Existing defenses against behavioral fingerprinting fall into three camps, none sufficient:

- **Browser anti-fingerprint** (Brave, LibreWolf, Tor Browser): touch the network and JavaScript layer only. They can fake screen size or canvas hash, but cannot lie about how the user actually moved the mouse — that signal leaks straight from the OS.
- **Privacy extensions** (Privacy Badger, uBlock Origin): block known trackers, but cannot poison the signal that leaks through allowed scripts (reCAPTCHA, Cloudflare Turnstile, bank fraud-detection).
- **RPA / automation tools** (Keyboard Maestro, BetterTouchTool, Hammerspoon): inject synthetic input, but make it MORE robotic, not less — they're trivially detected by the same systems we want to defeat.

MIRROR differs by combining four properties no existing tool has together:

1. **System-level, not browser-level.** Operates at CGEventTap, the same layer the OS uses internally — invisible to apps.
2. **Modification, not injection.** Preserves real human intent, adds statistical noise on top. The output is "real human + jitter", not "synthetic input".
3. **Cross-application.** Defeats biometrics in browsers, banking apps, IDEs, anywhere the user types or clicks.
4. **Profile-aware downgrade.** Automatically reduces noise on password fields to prevent typos without disabling the defense.

This is the first system-level behavioral-biometrics jammer on macOS, open-source or otherwise.

---

## 3. Algorithm

MIRROR operates in a single passive mode: in-flight event modification via CGEventTap.

### Event interception pipeline

CGEventTap intercepts every user input event before delivery to apps.
For each event, MIRROR:

  1. Reads event type (mouseMoved, leftMouseDown, keyDown, scrollWheel, etc.)
  2. Checks frontmost app against exclusion list — if excluded, passthrough unchanged
  3. Checks if focused field is NSSecureTextField — if yes, force profile = light
  4. Generates noise from HW RNG (Apple Silicon mrs RNDR) seeded ChaCha20 PRNG
  5. Applies profile-specific perturbation
  6. Returns modified event to event queue

### Per-event perturbation rules

| Event              | Modification                                          |
|--------------------|-------------------------------------------------------|
| Mouse move         | Add Gaussian noise to (dx, dy), σ scaled by profile   |
| Mouse click        | Shift press/release timing by ±Δ ms                   |
| Key down           | Jitter dwell time (key-hold duration) by ±Δ ms        |
| Key up             | Jitter flight time (gap to next key) by ±Δ ms         |
| Scroll wheel       | Perturb wheel delta and velocity curve                |

### Profile presets

| Profile  | Mouse σ  | Click Δ   | Dwell Δ   | Flight Δ  | Defeats                            |
|----------|----------|-----------|-----------|-----------|------------------------------------|
| light    | 0.5 px   | ±5 ms     | ±10 ms    | ±5 ms     | Simple ML classifiers              |
| medium   | 1.0 px   | ±15 ms    | ±25 ms    | ±20 ms    | Most behavioral fingerprinters     |
| heavy    | 2.0 px   | ±30 ms    | ±50 ms    | ±40 ms    | reCAPTCHA v3, advanced bank fraud  |

Default profile: **medium**. Configurable via IPC.

### Password field auto-downgrade

When frontmost focused field is `NSSecureTextField` (detected via Accessibility API):
  effective_profile = min(current_profile, light)
  
This prevents typo-inducing jitter on passwords while preserving baseline defense — a compromise between safety (passwords don't break) and exposure (some signal still leaks to keystroke fingerprinters).

---

## 4. Stack

| Component       | Tech                                       | Reason                                          |
|-----------------|--------------------------------------------|-------------------------------------------------|
| Core daemon     | C17                                        | CGEventTap is C API; zero-overhead requirement  |
| Event tap       | CGEventTap (ApplicationServices.framework) | Only stable system-wide input intercept on macOS|
| Timing          | mach_absolute_time                         | Nanosecond precision, no syscall overhead       |
| Entropy         | HW RNG (mrs RNDR inline asm) + ChaCha20    | True random seed, fast PRNG for high event rate |
| Focus detection | AXUIElementCopyAttributeValue (AppKit)     | Detect NSSecureTextField on frontmost window    |
| IPC with core   | UNIX socket + JSON-RPC 2.0                 | Same protocol as CHAFF/ECHO/ORACLE              |
| Build system    | clang -Wall -Wextra -Werror, Makefile      | Same as CHAFF                                   |

**Why C, not Python:** Event tap callback runs in the input event hot path. Any latency >1ms degrades user experience. Python overhead alone (~50-100μs per call) would be intolerable at 1000+ events/sec.

**Why CGEventTap, not IOKit HID:** IOKit gives raw device events but bypasses macOS input processing (key repeat, modifier state, IME). CGEventTap intercepts AFTER OS processing — apps see modified events as if they came naturally from the user.

**Why HW RNG + PRNG hybrid:** Pure HW RNG (~50ns per call) cannot sustain 1000+ events/sec without latency spikes. ChaCha20 reseeded from HW RNG every N events gives cryptographically strong randomness at PRNG speed.

---

## 5. IPC API

### Commands (core → mirror)

| Method                    | Params                              | Returns                                          |
|---------------------------|-------------------------------------|--------------------------------------------------|
| `mirror.status`           | none                                | `{enabled, profile, events_shaped_today}`        |
| `mirror.enable`           | none                                | `{ok, enabled: true}`                            |
| `mirror.disable`          | none                                | `{ok, enabled: false}`                           |
| `mirror.profile.set`      | `{profile: light\|medium\|heavy}`   | `{config}`                                       |
| `mirror.exclude.add`      | `{bundle_id}`                       | `{exclusions}`                                   |
| `mirror.exclude.remove`   | `{bundle_id}`                       | `{exclusions}`                                   |
| `mirror.exclude.list`     | none                                | `{exclusions: [bundle_id, ...]}`                 |
| `mirror.stats`            | none                                | `{counters_per_event_type}`                      |

### Events (mirror → core)

| Event                       | Payload                                                    |
|-----------------------------|------------------------------------------------------------|
| `mirror.profile.changed`    | `{old_profile, new_profile, reason}`                       |
| `mirror.permission.lost`    | `{}` — user revoked Accessibility access                   |
| `mirror.tap.disabled`       | `{reason}` — system disabled tap (timeout, error)          |
| `mirror.error`              | `{code, message, recoverable: bool}`                       |

---

## 6. Dependencies

System:
- macOS 14+ (CGEventTap API stability)
- Accessibility permission (System Settings → Privacy & Security → Accessibility)
- ApplicationServices.framework (system-shipped)
- Code signing (CGEventTap requires signed binary on macOS 26+)

Build:
- clang with C17 support
- Make
- No external libraries (system frameworks only)

Runtime footprint:
- Binary size: ~3 MB
- RAM: <10 MB resident
- CPU: <0.5% at idle, <2% under sustained input
- Event latency: <100μs added per event (target)

Project-internal:
- `~/.config/chimera/mirror/config.json` — profile, exclusions
- IPC socket via core (no direct sockets)

Network: MIRROR makes NO outbound network calls. Pure local OS-layer module.

---

## 7. Security model

### Protects against
- Behavioral biometrics: mouse curve analysis, keystroke dynamics (dwell/flight time)
- reCAPTCHA v3 invisible scoring (relies heavily on mouse movement entropy)
- Bank and SaaS fraud-detection systems that profile typing rhythm
- Cross-site behavioral fingerprinting (correlation across sessions and sites)
- Stylometry of input patterns (some advanced fingerprinters)

### Does NOT protect against
- Server-side adaptive ML that learns to subtract MIRROR's noise distribution over weeks/months
- Hardware-level keyloggers (USB interposer, EM emanation, OS-level kexts)
- Compromised MIRROR daemon itself — it sees every keystroke; if compromised, full keylogger
- High-precision input devices that bypass CGEventTap (Wacom pressure curves, gamepad axes in some games)
- Content-based fingerprinting (what you type, not how you type it)

### Privacy invariant
MIRROR NEVER logs event payload — no key codes, no coordinates, no timestamps of specific events.
Only aggregate counters of events shaped (per event type, per day) are kept in memory.
No persistence of input data to disk. Ever.

### Threat model assumptions
- Adversary cannot read MIRROR process memory (System Integrity Protection enforced)
- Adversary cannot modify MIRROR binary (code-signed, integrity verified at launch)
- Accessibility permission is granted by the user knowingly and is auditable in System Settings
- The user trusts the OS kernel and CGEventTap subsystem itself

---

## 8. Open questions

These need decisions before implementation begins:

- **Per-app exclusion strategy.** Explicit blocklist (games, music production apps, drawing tablets) maintained by user vs opt-in passthrough mode where MIRROR is off by default and only enabled per app. Trade-off: usability vs security default.
- **Profile selection heuristic.** Should profile auto-switch based on frontmost app type? (e.g. `light` in IDEs, `heavy` in browsers). Or always manual?
- **HW RNG batching.** How many ChaCha20 reseeds per second? Trade-off: HW RNG calls cost ~50ns each; too frequent = latency, too rare = predictability.
- **macOS Tahoe (26) tightening.** CGEventTap may require Endpoint Security entitlement in future macOS versions. Plan B: fall back to per-app injection via Accessibility API (slower, narrower coverage).
- **Scroll perturbation aggressiveness.** Heavy scroll jitter is disorienting for users. Should scroll ALWAYS be `light` regardless of profile? Or expose separate scroll profile?
- **Event tap timeout handling.** macOS disables event taps that take >1s in callback. What's the fallback when system disables our tap mid-session? Auto-restart? Notify user?

To be resolved during implementation.

---

## 9. Status

**Planned.** No code yet.

Depends on:
- Core orchestrator with IPC infrastructure (UNIX socket + JSON-RPC 2.0)
- Code-signing infrastructure for the chimera build (CGEventTap requirement)
- Accessibility permission flow from core (user-facing prompt + retry logic)

After MIRROR works, the human-machine interface layer is defended. Combined with CHAFF + ECHO (network) and ORACLE (system reasoning), CHIMERA covers four of five major fingerprinting surfaces. PULSE will close the cognitive surface.

No imitations. No stubs. (See MANIFESTO §4.)
