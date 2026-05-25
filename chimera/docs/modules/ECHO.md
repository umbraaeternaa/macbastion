# §5.2 ECHO — Bandwidth Normalizer

Module: `echo`
Codename origin: echo chambers — the input pattern is transformed into a flat, repeating output regardless of source
Status: **Planned** (second CHIMERA module, after CHAFF)
Target version: chimera v0.3.0
Estimated effort: 2-3 working sessions (~8 hours)

---

## 1. Mission

Reshape the user's outbound traffic into a constant-rate flow.

Regardless of whether the user is idle, watching video, or downloading a large file — the observable bandwidth shape on the wire is the same: a flat line of X KB/s.

This eliminates volume-based fingerprinting in its strongest form: the adversary cannot tell from traffic shape whether you are sleeping, working, or panicking.

---

## 2. Why unique

The technique itself (constant-rate padding) is well-known in academia since the 1990s. Production implementations are absent because:

- **Tor** uses variable-rate padding (LET, conflux) — not constant.
- **VPNs** never pad. They optimize for throughput, not anonymity.
- **Mullvad's DAITA** (Defense Against AI-guided Traffic Analysis) was announced 2024 but ships only inside Mullvad VPN. Not a reusable tool.
- **Academic prototypes** (Anonymous Padding, Tamaraw, BuFLO) live in research papers, not as installable software.

ECHO differs:

1. **Local, not endpoint-based.** Works on the user's machine, independent of any VPN/Tor configuration.
2. **Composable.** Can stack with CHAFF, with Tor, with Mullvad. Each layer adds defense.
3. **Open and auditable.** Full source, no vendor lock-in.
4. **Application-agnostic.** Pads at the network interface level via pf — any traffic from any app gets normalized.

This is the first general-purpose, open-source, end-user-installable constant-rate padder for macOS.

---

## 3. Algorithm

ECHO operates as a packet-level shaper between application sockets and the physical network interface.
configuration:
TARGET_RATE_KBPS = 100        # default bandwidth budget
BURST_TOLERANCE = 200          # short bursts allowed up to this
PADDING_PROTOCOL = "udp/443"   # padding packets mimic QUIC
every TICK_MS (default 10ms):
real_bytes_queued = pf_queue_size()
real_bytes_to_send = min(real_bytes_queued, TARGET_RATE_KBPS / 100)
if real_bytes_to_send < TARGET_RATE_KBPS / 100:
    padding_bytes = (TARGET_RATE_KBPS / 100) - real_bytes_to_send
    emit_padding_packet(padding_bytes)

pf_dequeue_and_send(real_bytes_to_send)

Padding packets are UDP/443 (looks like QUIC). They are addressed to a known echo-sink — either a local loopback discarder, or a peer on the public internet that drops them silently (cooperating volunteer infrastructure, optional).

On the receive side, ECHO does NOT pad inbound traffic — adversaries controlling the user's upstream see normalized outbound only. Inbound shaping requires server cooperation and is out of scope.

---

## 4. Stack

| Component       | Tech                       | Reason                                                 |
|-----------------|----------------------------|--------------------------------------------------------|
| Core daemon     | C17                        | Tight timing (10ms tick), no GC                        |
| Packet I/O      | pfctl + BPF                | macOS kernel hooks for packet capture/inject           |
| Timer           | kqueue EVFILT_TIMER        | Sub-millisecond accuracy via mach_absolute_time        |
| Stats / state   | Shared memory + atomics    | Avoid lock contention on the hot path                  |
| IPC with core   | UNIX socket + JSON-RPC     | Same protocol as CHAFF                                 |
| Build system    | Make + clang               | Same as CHAFF                                          |

**Why C, not Python:** packet shaping demands sub-millisecond predictability. Python is ~1000× too slow and too jittery.

**Why pfctl + BPF and not a kernel extension:** macOS Big Sur deprecated third-party kexts. BPF filtering and pf anchors are the sanctioned way to do packet-level work without breaking SIP.

---

## 5. IPC API

### Commands (core → echo)

| Method                | Params                                  | Returns                                              |
|-----------------------|-----------------------------------------|------------------------------------------------------|
| `echo.status`         | none                                    | `{running, current_rate_kbps, real_kbps, pad_kbps}`  |
| `echo.start`          | `{target_kbps?}`                        | `{started_at, effective_rate}`                       |
| `echo.stop`           | none                                    | `{stopped_at, stats}`                                |
| `echo.config.set`     | `{target_kbps?, burst_tolerance?}`      | `{config}`                                           |
| `echo.config.get`     | none                                    | `{config}`                                           |
| `echo.stats`          | `{window: "1m"/"1h"/"1d"}`              | `{histogram, padding_ratio}`                         |

### Events (echo → core)

| Event                    | Payload                                                  |
|--------------------------|----------------------------------------------------------|
| `echo.rate.violation`    | `{expected_kbps, observed_kbps, duration_ms}`            |
| `echo.padding.surge`     | `{padding_ratio_pct}` — fired if padding > 80% sustained |
| `echo.error`             | `{code, message, recoverable: bool}`                     |

---

## 6. Dependencies

System:
- `pfctl` (preinstalled on macOS)
- BPF device (`/dev/bpf*`)
- root privileges for raw socket operations

Project-internal:
- pf anchor file (`/etc/pf.anchors/com.chimera.echo`)
- Padding endpoint config (`~/.config/chimera/echo/sinks.json`)
- Stats DB (`~/.config/chimera/echo/stats.db`)

Network: cooperates with CHAFF (if running) by accounting CHAFF traffic as "real" — otherwise CHAFF and ECHO would double-count.

---

## 7. Security model

### Protects against
- Volume-based traffic fingerprinting
- Idle-vs-active inference from off-hours bandwidth dips
- Burst detection on file uploads
- Bandwidth correlation across multiple sites visited

### Does NOT protect against
- Timing-based attacks at sub-tick resolution (mitigated by short tick, but not eliminated)
- Adversaries who can compromise the destination endpoint
- Long-term statistical attacks if the user disables ECHO sometimes
- Power-side-channel attacks on the device itself

### Threat model assumptions
- Adversary measures traffic volume per second at the user's gateway
- Adversary cannot decrypt HTTPS
- User does not enable/disable ECHO frequently (this leaks)

---

## 8. Open questions

- **Default rate?** 100 KB/s burns ~250 MB/day. Acceptable on home WiFi, painful on tethered 4G. Adaptive rate?
- **Padding sink?** Local discard is simplest but doesn't actually hit the wire — adversary still sees nothing. Real remote sink is needed; do we use a single canonical one (Cloudflare workers?) or a small list?
- **Interaction with VPN?** If user runs Mullvad, ECHO pads BEFORE VPN encryption. Mullvad's DAITA pads AFTER. Which order is more protective? (Probably ECHO before, but needs measurement.)
- **Cellular mode?** Hard-disable ECHO on metered connections to avoid silent data overage. Default behavior?

To be resolved during implementation.

---

## 9. Status

**Planned.** No code yet.

Depends on CHAFF being implemented first (shares profile data and IPC infrastructure). Cannot ship before CHAFF reaches stable.

No imitations. No stubs. (See MANIFESTO §4.)
