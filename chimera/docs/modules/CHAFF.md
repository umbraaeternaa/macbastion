# §5.1 CHAFF — Traffic Obfuscator

Module: `chaff`
Codename origin: military term for radar countermeasure — strips of metal foil dropped to confuse enemy radar
Status: **Planned** (first CHIMERA module to be implemented)
Target version: chimera v0.2.0
Estimated effort: 2 working sessions (~6 hours)

---

## 1. Mission

Generate contextual decoy HTTPS traffic that statistically masks the user's real browsing patterns from passive observers: ISPs, exit-node correlators, traffic-analysis adversaries, behavioral-fingerprinting ML classifiers.

The real signal becomes indistinguishable from noise.

---

## 2. Why unique

Existing solutions are insufficient:

- **Tor pluggable transports (obfs4, meek)** hide that you USE Tor, but don't hide WHEN you browse or WHAT volume of data flows through you.
- **Apple iCloud Private Relay** protects Safari traffic only. Everything else (Chrome, Telegram, native apps) leaks.
- **Random-noise generators** (Noisy, Internet Noise, RuinMyHistory) produce clearly-fake traffic — uniform timing, random domains, no contextual realism. Modern ML classifiers filter them out trivially.
- **VPNs** hide your IP but not your traffic shape. An adversary watching encrypted volume can still fingerprint behavior.

CHAFF differs by four properties no other tool combines:

1. **Profile-based.** Observes the user's REAL traffic shape over 7 days (hours of activity, packet sizes, request frequencies) before generating anything.
2. **Statistically matched.** Decoys mirror the user's profile — same hourly distribution, same size histogram, same inter-request timing.
3. **Real endpoints.** Decoys hit actual public HTTPS sites (Wikipedia, BBC, GitHub, HackerNews) — not synthetic domains an observer would flag.
4. **Volume amplification.** Target volume is 10× the user's real volume. Real signal hides in noise of the user's own behavioral shape.

No equivalent exists in open source or commercial security tools as of this writing.

---

## 3. Algorithm

CHAFF operates in two phases.

### Phase A — Profiling (passive observation, 7 days)
on each outbound HTTPS connection observed via pf/dtrace:
record {
timestamp_utc,
destination_category,    # news, tech, social, search, dev
bytes_sent,
bytes_received,
duration_ms,
}
build per-hour histograms:
profile[hour] = {
mean_requests,
size_distribution_bytes,
category_weights,
inter_request_gap_ms,
}

Profiling is silent. No decoys generated during this phase.

### Phase B — Generation (active, continuous)
loop forever:
hour = current_local_hour
target_volume = profile[hour].mean * MULTIPLIER     # default 10x
sent_volume = bytes_sent_this_hour_by_chaff
if sent_volume >= target_volume:
    sleep(60)
    continue

endpoint = weighted_pick(profile[hour].category_weights)
request_size = sample_from(profile[hour].size_distribution_bytes)
jitter_ms = max(50, gauss(mu=profile[hour].inter_request_gap_ms, sigma=300))
sleep_ms(jitter_ms)

perform_https_get(endpoint, request_size)
record_event(chaff.request.sent, endpoint, request_size)

ARM64 Assembly is used for sub-microsecond timing jitter via the CNTVCT_EL0 cycle counter — software clocks alone are insufficient for indistinguishability.

---

## 4. Stack

| Component        | Tech                       | Reason                                                    |
|------------------|----------------------------|-----------------------------------------------------------|
| Core daemon      | C17                        | 24/7 uptime, predictable latency, no GC pauses            |
| HTTPS client     | libcurl (system .dylib)    | Mature, audited, statically link unnecessary              |
| Timing jitter    | ARM64 Assembly             | CNTVCT_EL0 cycle counter, sub-microsecond precision       |
| Profile storage  | SQLite + Fernet (AES-128)  | Encrypted at rest, queryable, atomic writes               |
| IPC with core    | UNIX socket + JSON-RPC 2.0 | Standard, debuggable, fits CHIMERA's protocol             |
| Build system     | Make + clang               | No dependencies beyond Xcode CLT                          |

**Why C, not Python:** the daemon runs continuously and must not interfere with real user traffic timing. Python's GC pauses and memory overhead are unacceptable.

**Why ARM64 Asm:** the difference between "human" and "automated" traffic is timing precision below 1ms. The Mach time API has ~100µs jitter. Reading CNTVCT_EL0 directly gives ~10ns precision.

---

## 5. IPC API

### Commands (core → chaff)

| Method                  | Params                          | Returns                              |
|-------------------------|----------------------------------|---------------------------------------|
| `chaff.status`          | none                             | `{phase, running, requests_today, bytes_today}` |
| `chaff.profile.start`   | `{duration_days: int}`           | `{started_at}`                        |
| `chaff.profile.stop`    | none                             | `{profile_summary}`                   |
| `chaff.generation.start`| none                             | `{started_at}`                        |
| `chaff.generation.stop` | none                             | `{stopped_at, total_decoys_sent}`     |
| `chaff.config.set`      | `{multiplier?, max_bandwidth?}`  | `{config}`                            |
| `chaff.endpoints.list`  | none                             | `{endpoints: [...]}`                  |
| `chaff.endpoints.add`   | `{url, category}`                | `{ok}`                                |

### Events (chaff → core)

| Event                       | Payload                                              |
|-----------------------------|------------------------------------------------------|
| `chaff.profile.progress`    | `{day, total_requests_observed}`                     |
| `chaff.profile.completed`   | `{histogram_summary}`                                |
| `chaff.request.sent`        | `{endpoint, size_bytes, duration_ms}`                |
| `chaff.error`               | `{code, message, recoverable: bool}`                 |

All payloads are JSON. All endpoint URLs and statistics are encrypted at rest.

---

## 6. Dependencies

System (already present on macOS):
- libcurl (`/usr/lib/libcurl.dylib`)
- SQLite3 (`/usr/lib/libsqlite3.dylib`)
- Xcode Command Line Tools (clang, make, ld)

Project-internal:
- Decoy endpoint whitelist (`chimera/modules/chaff/endpoints.json`) — ~50 public HTTPS sites, categorized
- Profile DB (`~/.config/chimera/chaff/profile.db`) — created on first run
- IPC: connects OUT to core (`~/.config/chimera/run/core.sock` commands + `events.sock` events); CHAFF binds no socket of its own (§6.3, star topology §6.2)

Network: this is the ONLY CHIMERA module that legitimately makes outbound network calls. All other modules are local-only.

---

## 7. Security model

### Protects against
- Passive traffic-volume analysis by ISP
- Timing correlation by Tor exit-node observers (when used with Tor)
- Volume-based fingerprinting by passive eavesdroppers
- Behavioral ML classifiers trained on hour-of-day activity patterns

### Does NOT protect against
- Active attackers who can trigger user's real requests on demand (e.g. by sending a phishing link)
- Endpoint-level surveillance — if you log into Gmail, Google still knows
- DNS-leak attacks — separate module's responsibility (ORACLE + DNS hardening)
- Same-host malware that reads browser memory directly
- Adversaries with global passive observation capabilities (NSA-class)

### Threat model assumptions
- Adversary sees encrypted HTTPS traffic volume and timing
- Adversary does NOT see decrypted content
- Adversary has no access to user's machine
- Adversary may use ML models on observed traffic shape

---

## 8. Open questions

These need decisions before implementation begins:

- **Profiling without consent for embedded apps?** If Chrome is running and visiting sites, do we profile that without explicit per-app opt-in?
- **Bandwidth cap default?** Hard limit on chaff bandwidth to avoid exhausting capped cellular plans.
- **Behavior during VPN/Tor toggle?** Should chaff pause when user explicitly enables Tor (less needed) or continue (more cover)?
- **Endpoint health checking?** If wikipedia.org is unreachable from a particular network, do we silently rotate endpoints or alert?

To be resolved during implementation.

---

## 9. Status

**Planned.** No code yet.

This document is the canonical specification. When implementation begins, it becomes the contract: every property listed here must be true in working code, or this document must be updated to reflect reality.

No imitations. No stubs. (See MANIFESTO §4.)
