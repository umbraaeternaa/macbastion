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

## 3. Locked decisions (EP-1 … EP-8)

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
