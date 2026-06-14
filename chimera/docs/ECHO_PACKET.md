# §8 Amendment A1 — Privileged packet-shaper (ECHO traffic normalization)

> Formal §8 amendment to ARCHITECTURE §8.8 ("Any addition to the root surface requires a
> formal §8 amendment, not a code change"). It admits ONE new privileged domain — a packet-
> shaper for ECHO — and enumerates exactly what it may do. This is the deliberate review the
> §8.8 gate demands. **No code ships from this document; it is the decision record that
> authorizes the later, gated implementation.** Companion to `SHIM.md` (resolves SH-12).

> Status: **LOCKED** — ratified by the operator Day 21 (2026-06-13). Implementation is gated (§5); per-command root approval required.

---

## 1. Why this amendment exists

ECHO's real effect — holding the network interface at a **constant traffic rate** so volume
fingerprinting sees a flat line — requires packet-plane work: a `pf` anchor
(`/etc/pf.anchors/com.chimera.echo`), `pfctl`, and BPF/raw-socket pacing. All of that needs
**root**.

The privileged shim (§8.8) **cannot** carry it: an invariant of the shim is that it *never
opens network sockets*. Smuggling packet I/O into the shim would break that boundary and bloat
the one root component we keep deliberately tiny. SH-12 (SHIM.md, locked 2026-06-04) therefore
ruled packet-root **OUT of the shim**, pending "a separate §8 amendment or a dedicated packet-
helper domain." **This is that amendment.**

Minimal-root (MANIFESTO §1/§6, §8.8) does **not** mean zero-root — it means every root
capability passes deliberate, enumerated review. This document is that review for ONE narrow
new domain.

---

## 2. The decision

Admit a **separate, minimal, root LaunchDaemon — `chimera-echo-shaper`** — distinct from the
4-op shim, whose ONLY job is ECHO's pf-anchor lifecycle + constant-rate pacing. The shim and
its invariants are untouched.

### Enumerated capability — the shaper does ONLY:

| # | Capability | Triggered by |
|---|------------|--------------|
| 1 | Load/refresh ECHO's pf anchor (`com.chimera.echo`) with the current rate | ECHO daemon, operator opt-in |
| 2 | Run the constant-rate pacer over that anchor (BPF/raw socket) | ECHO daemon |
| 3 | Remove its pf anchor + stop pacing (restore normal flow) | ECHO stop, crash, or operator off |

### The shaper NEVER (the boundary into root, mirrors the shim's never-list):

- reads packet **payloads** / decrypts anything (it shapes *volume/timing* only)
- opens arbitrary sockets or contacts arbitrary endpoints
- touches any `pf` rules other than its own `com.chimera.echo` anchor
- executes operator-provided code
- persists captured traffic anywhere
- accepts commands from anything but the authenticated user-level core/ECHO

---

## 3. Locked decisions (EP-1 … EP-10)

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| **EP-1** | Where packet-root lives | **Separate `chimera-echo-shaper` LaunchDaemon**, NOT the shim | Preserves the shim's "never opens sockets" invariant (§8.8); resolves SH-12 |
| **EP-2** | Capability scope | The 3 enumerated ops above + the never-list | Narrow, auditable, single-purpose root surface |
| **EP-3** | Failure mode | **FAIL-OPEN for the network** | A traffic component must NEVER wedge connectivity — if the shaper dies it removes its anchor and real traffic flows normally. (Inverts the usual fail-closed: availability > obfuscation here.) |
| **EP-4** | Default state | **Opt-in, OFF by default** | Default install adds NO new root; ECHO runs its userspace logic, the shaper is installed/activated only on explicit operator config (like PURGE Tier-2) |
| **EP-5** | Authentication | UNIX socket + **peercred + per-boot secret**, code-sig-attested peer (the shim's SS-* model) | Same proven trust model; only the attested core/ECHO may command it |
| **EP-6** | The padding "sink" (the §8 open question) | **Pace REAL + CHAFF traffic up to the rate — padding rides CHAFF's real outbound HTTPS, not /dev/null** | Discarded padding fools no on-path observer. CHAFF already emits real decoy HTTPS to real endpoints; ECHO fills the gap to constant-rate with it. Honest limit: with CHAFF off, ECHO cannot fully normalize (documented, not faked) |
| **EP-7** | Reuse | Defined for ECHO; **CHAFF Phase A may later reuse this domain** (its own amendment if scope grows) | One reviewed packet domain, not many |
| **EP-8** | Accepted residual risk (T5) | A compromised shaper could see ECHO-anchor traffic *volume/timing* (never payloads) and could disable shaping | Bounded blast radius; mitigated by EP-1/2/4/5 + minimal auditable code |
| **EP-9** | Where the required main-ruleset hook is installed (added Day 22 after live validation, §7) | **Install-time, ONCE** — `dummynet-anchor "com.chimera.echo"` is added to `/etc/pf.conf` at opt-in install (operator-approved, with backup) as a **FILE edit that activates at the NEXT REBOOT — never a live `pfctl -f`**; the **runtime daemon touches ONLY its own anchor** | F1 (§7) proved a bare sub-anchor is inert — a parent hook is required. Confining the single main-ruleset touch to a one-time, audited install action preserves EP-2's runtime boundary. **Hard lesson (Day 22): the first live deploy ran `pfctl -f /etc/pf.conf` and it FLUSHED dynamically-inserted system anchors → the operator's Wi-Fi dropped. A live reload of the main ruleset is forbidden; the hook loads at boot like the stock com.apple anchors.** Narrow exception to the §2 never-list, ratified by the operator Day 22 (2026-06-14) |
| **EP-10** | `shaper.handshake` authentication (added Day 22, C2a) | **peercred-only** — the per-boot secret is handed to any peer the kernel reports as the operator uid; NO SecCode attestation | The shaper's ops are FAIL-OPEN / low-stakes (EP-8: volume/timing only, never payloads), unlike the shim's destructive ops where SecCode attestation is warranted. Adding it would force a Security/CoreFoundation framework onto the deliberately minimal, no-framework shaper. Narrow deviation from EP-5's "attested peer" wording, ratified by the operator Day 22 (2026-06-14) |

---

## 4. Threat analysis (what this costs)

- **Added attack surface:** one more root process on every machine that opts in. Mitigated by
  EP-2 (narrow), EP-5 (authed), minimal/auditable code, and EP-4 (absent unless opted in).
- **Not a payload risk:** the shaper works on volume/timing, never reads or decrypts content
  (EP-2 never-list) — so a compromise leaks far less than a generic root process.
- **Availability:** EP-3 fail-open guarantees a shaper bug cannot break the user's network.
- **Honest limits (MANIFESTO §4):** ECHO defeats *volume* fingerprinting, not sub-tick timing,
  endpoint compromise, or power side-channels (ECHO.md §7). With CHAFF off, normalization is
  partial (EP-6). Constant-rate burns bandwidth (metered-connection guard is an ECHO config).

---

## 5. What ships after ratification (gated, separate slices)

1. `chimera-echo-shaper` skeleton (RED→GREEN, fail-OPEN no-op pf path first, §4-honest).
2. pf-anchor load/remove (tested on a throwaway anchor; never the user's live pf rules).
3. The constant-rate pacer + CHAFF cooperation (EP-6).
4. Opt-in install/uninstall (separate from the shim; `deploy/`), auth (EP-5).

Every privileged step is run only with the operator's explicit per-command approval
(root-access protocol) and tested before it touches anything live.

---

## 6. Status

**LOCKED** — ratified by the operator Day 21 (2026-06-13). ARCHITECTURE §8.8.1 points here,
SHIM.md SH-12 records the track as taken, ECHO.md §9 reflects it. Implementation ships as the
gated slices in §5, each with per-command root approval. (MANIFESTO §4 — decision record; the
code is still to come, nothing is faked.)

---

## 7. Live-pf validation (Day 22, 2026-06-14) — proven recipe + findings

EP-2's pf-anchor path was validated on the operator's LIVE kernel (M2, macOS 26, pf already
Enabled). A throwaway dummynet pipe + anchor was loaded, measured, and torn down with full
restore — per-command operator approval, FAIL-OPEN throughout. No persistent change.

### Result (measured)

- Baseline download: ~5.1–6.0 MB/s.
- With `dnctl pipe 1337 config bw 2Mbit/s` + `dummynet in all pipe 1337`: **229,831 B/s ≈
  1.84 Mbit/s** — right at the cap. `dnctl show` confirmed traffic through pipe 1337
  (2.88 MB, with drops enforcing the rate). ~25× reduction; restore to stock clean.
- **ECHO bandwidth shaping works on this kernel.**

### Proven recipe (what actually shapes)

1. Install a parent hook: load a SUPERSET main ruleset = stock `/etc/pf.conf` **plus one line**
   `dummynet-anchor "com.chimera.echo"`, via `pfctl -f`.
2. `dnctl pipe 1337 config bw <rate>`.
3. Load the rule(s) into the hooked anchor: `pfctl -a "com.chimera.echo" -f <file>`, where the
   file holds `dummynet in all pipe 1337` (and/or `out`).
4. Restore: `pfctl -f /etc/pf.conf` ; `dnctl pipe 1337 delete`.

### Findings for the implementation (`echo-shaper/src/anchor.c`)

- **F1 — a parent hook is REQUIRED.** A sub-anchor loaded with `pfctl -a … -f` alone is INERT:
  the active ruleset had no `dummynet-anchor` for it (nesting under the stock `com.apple/*`
  hook did NOT carry the dummynet rule). The shaper must add its own
  `dummynet-anchor "com.chimera.echo"` to the main ruleset (superset load) and restore stock
  in `clear()`. The current `anchor.c` does only step 3 → it would load an inert anchor.
- **F2 — direction.** `dummynet out all` shapes only OUTBOUND; a download (inbound) is
  unaffected. Constant-rate normalization needs BOTH `in` and `out`. The CANDIDATE rule
  (out-only) is to be corrected to in+out.

### §2 never-list — narrow exception RATIFIED as EP-9 (Day 22)

F1 means the shaper needs a parent hook in the main pf ruleset, which the §2 never-list
("touches any `pf` rules other than its own `com.chimera.echo` anchor") otherwise forbids. The
operator ratified the narrow exception **option A — install-time** (EP-9):

> The `dummynet-anchor "com.chimera.echo"` line is added to `/etc/pf.conf` ONCE at opt-in
> install (operator-approved, with a stock backup). The anchor is empty until the daemon loads
> its rules, so the line is inert while ECHO is off. The RUNTIME daemon touches ONLY its own
> `com.chimera.echo` anchor (`pfctl -a`) + the dummynet pipe — it never reloads the main
> ruleset. Uninstall removes the line; FAIL-OPEN (a flushed/empty anchor passes all traffic).

This confines the single main-ruleset touch to install-time and preserves EP-2's runtime
boundary. The locked EP-1…EP-8 are unchanged; EP-9 records this exception.

---

## 8. EP-6 floor-filling — design + deferral (Day 22)

EP-6 (the §3 "padding sink" decision) resolved that ECHO's padding rides CHAFF's real outbound,
not /dev/null. With the packet-shaper now complete, here is the honest state of the padding
itself.

### What "constant-rate" needs

A flat on-wire line has two halves:

- **Ceiling** — cap the rate at R so bursts can't spike the line. **DONE**: the kernel dummynet
  pipe (`dnctl pipe … config bw R`, validated §7) holds this in-kernel, both directions.
- **Floor** — when the operator is idle, real traffic drops below R and the line sags; to keep
  it flat, idle bandwidth must be *filled* up to R with padding. **NOT built.**

### The model already exists (userspace)

`modules/echo` already computes the floor decision purely: `echo_shape(queued, budget, burst)`
returns `{real_send, padding}` with `padding = max(0, budget - real_send)` — exactly the bytes
needed to hold the wire at `budget`. What is missing is *running* it against the real wire.

### Why a faithful implementation is a research-grade feedback loop

The `echo_shape` model assumes ECHO mediates the byte stream (it sees `queued`). The real
architecture does NOT: shaping lives on the packet plane (pf/dummynet via the shaper), where
ECHO never sees individual bytes. A faithful floor-filler is therefore a closed loop:

1. measure the current outbound rate (the shaper's `dnctl show` pipe byte counters),
2. compute the deficit `R − current`,
3. drive CHAFF to emit ~that many bytes of real decoy traffic (EP-6: ride CHAFF, never
   /dev/null) — CHAFF today exposes start/stop + a multiplier, not "emit exactly N bytes".

### Status: DESIGNED, DEFERRED (MANIFESTO §4)

Deferred deliberately, not forgotten:

- The **ceiling** (the main volume-fingerprint win) is already live in-kernel.
- The floor's marginal benefit is **threat-model-dependent** and it **burns bandwidth**
  continuously (a real cost on a metered link) — so it is rightly opt-in and not default.
- A half-wired floor-filler would be an imitation (§4). The honest move is to record the design
  here and ship the complete, real ceiling now; the loop is re-opened when the threat model
  justifies its cost. `shaper.pace` stays an explicit no-op until then (the userspace pacer the
  original spec imagined is largely vestigial — dummynet paces in-kernel).
