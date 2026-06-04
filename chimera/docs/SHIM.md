# Privileged Shim — Implementation Decisions (§7.10 / §8.8)

> Design record. Multi-session work. ARCHITECTURE §8.8 is the authoritative
> security boundary; this records HOW we implement within it (not new scope).
> Updated: 2026-06-04

---

## 1. Authoritative scope (restated from §8.8 — NOT re-litigated)

The root LaunchDaemon shim does ONLY these four operations and refuses anything
else. This list IS the security boundary into root.

| # | Capability                       | Triggered by              |
|---|----------------------------------|---------------------------|
| a | Lock screen / activate screensaver | TETHER L1, operator     |
| b | Evict CHIMERA Keychain items     | PURGE Tier 0              |
| c | Force-reboot                     | PURGE post-action        |
| d | Force-killall on shutdown timeout | Core §7.7 shutdown       |

The shim **never**: opens network sockets, reads file content, executes
operator-provided code, or accepts commands from anything other than the
user-level core (authenticated via a per-boot shared secret).

**Any addition to this list requires a formal §8 amendment, not a code change.**
This file does not expand the boundary — it records how we build inside it.

---

## 2. What the shim is NOT (gaps surfaced 2026-06-04)

- **Packet-plane root is OUT (SH-12).** CHAFF Phase A (pf/dtrace) and ECHO
  (pfctl/BPF/raw socket, `/dev/bpf*`, `/etc/pf.anchors/com.chimera.echo`) need
  packet-level root, which §8.8 forbids ("never opens network sockets"). This is
  a separate future track: a §8 amendment or a dedicated packet-helper domain —
  NOT this shim.
- **CHAFF code ↔ §8.8 contradiction.** `chaff.profile.*` returns
  `required_capability='privileged_shim'` (commands.c), but §8.8 grants no
  packet capability. CHAFF Phase A stays gated (-31004) even after this shim
  ships, until that gap is resolved.
- **VAULT is not unblocked by the shim.** VAULT's blocker is Keychain /
  Secure-Enclave **entitlements** (code-signing + TCC), not root. The shim only
  *evicts* Keychain items for PURGE (op b); it does not *grant* Keychain access.
- **launchd core-restart ≠ §8.8 ops.** Restarting core if it dies is launchd's
  job (a LaunchAgent KeepAlive plist), separate from the §8.8 privileged-ops
  shim. §7.10 prose conflates "supervisor" with "privileged-ops helper"; they are
  distinct concerns.

---

## 3. Locked decisions (SH-1 … SH-12)

| ID | Decision area | Chosen | Rationale / trade-off |
|----|---------------|--------|-----------------------|
| SH-1 | Process model | (a) separate C LaunchDaemon binary (root) | Per §7.10; minimal; mirrors the CHAFF/MIRROR native-module stack |
| SH-2 | Shim ↔ core IPC | (a) separate privileged socket `/var/run/chimera-shim.sock` (root-owned, 0600) + JSON-RPC envelope | Keeps the privileged plane distinct from core.sock; reuses the wire format |
| SH-3 | Privilege acquisition | (b) `launchctl bootstrap` + `.plist` in `/Library/LaunchDaemons/` | Direct, no app bundle; manual root-plist install. Signing tail shared with MIRROR |
| SH-4 | Operation interface | (a) core-proxy (module → core → shim) | Privilege separation: a module never holds the shim secret; §8.8 "only core talks" |
| SH-5 | Security validation | (a)+(b)+(c): per-boot shared secret + `LOCAL_PEERCRED` (core-uid only) + structured op enum | Defense-in-depth; minimizes injection surface; matches §8.8 auth |
| SH-6 | First slice scope | (c) NO-OP security skeleton (channel + auth + whitelist; real ops next slice) | Safest RED — builds the security boundary on zero destructive effect |
| SH-7 | Testing without root | (a) hermetic protocol/auth/whitelist (mock exec) + manual `-m privileged` tier | Realistic for CI; real effects never in CI |
| SH-8 | launchd integration | (a) plist registration deferred (binary + protocol first) | Smaller RED; run by hand for tests; signing not required yet |
| SH-9 | Language | (a) C17 (`-Wall -Wextra -Werror`) | Stack-consistent; syscalls (reboot/kill) natural; Swift not in the CHIMERA stack |
| SH-10 | Failure mode | (a) graceful degrade — shim down → -31004 | Consistent with CHAFF/MIRROR gating; CHIMERA keeps running |
| SH-11 | Destructive op safety | (a) reboot never in autotests (stubbed; config-flag + double-confirm) | Safety over coverage; dry-run/stub for destructive ops |
| SH-12 | Packet-plane root | (a) CHAFF/ECHO packet-root OUT — separate §8 amendment track | Honest to the §8.8 boundary; does not smuggle sockets into the shim |

---

## 4. Recommended first slice (SH-6 = c, detail)

A NO-OP **security skeleton** — the root surface with zero real privileged ops:

- privileged socket (`/var/run/chimera-shim.sock`, root, 0600)
- per-boot shared-secret authentication (core ↔ shim)
- `LOCAL_PEERCRED` peer check — accept the core uid only
- operation whitelist (exactly the §8.8 enum) + refuse-unknown
- structured op enum on the wire (no free-form strings / parameters)
- real ops (lock / evict / reboot / killall) are **no-op / logged-intent stubs**
  this slice — they land one at a time in subsequent slices

Tested: protocol/auth/whitelist hermetic with a mocked exec layer; real effects
behind a manual `-m privileged` tier. C17. launchd plist deferred.

---

## 5. Open questions before RED

- **Per-boot shared-secret mechanism.** §8.8 names it but does not specify how
  core and shim agree on the secret at boot (handoff, storage, rotation). Needs
  design before the auth path is real.
- **Code-signing prerequisite.** LaunchDaemon registration and trust need a
  signed binary — the same tail that gates the MIRROR CGEventTap. Both wait on
  signing infrastructure.
- **Login-window operation (§7.11 open Q).** Which modules (if any) must run
  before user login, and does that force more into the LaunchDaemon? Affects how
  early the shim must be available and what it must do pre-login.

---

## 6. Status

Preparation complete (2026-06-04). All SH-1…SH-12 locked; scope corrected against
§8.8 (4 ops, not 5 modules). **RED is a future dedicated session** — the
security-critical skeleton deserves full focus. No code yet. (MANIFESTO §4: no
stubs that pretend; this is a decisions record, not an implementation.)
