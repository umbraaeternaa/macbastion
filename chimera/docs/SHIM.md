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
| SH-5 | Security validation | (a)+(b)+(c): per-boot shared secret + `LOCAL_PEERCRED` (core-uid only) + structured op enum — ⚠️ **AMENDED 2026-06-05 → staged, see §5.3** | Defense-in-depth; minimizes injection surface; matches §8.8 auth |
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

## 5. Secret-handoff sub-design (SS-0 … SS-7)

> Resolves gap #4 ("per-boot shared-secret mechanism") at the design level.
> Records HOW the SH-5 auth path is built and *staged*. Preparation 2026-06-05 —
> no code.

### 5.1 Three findings that shaped the design

1. **Socket ownership (F1).** SH-2 sets the socket `root-owned, 0600`, but core is
   user-level (§7.10, LaunchAgent). A `connect()` needs write access to the socket
   file — a 0600 root socket is unreachable by non-root core. The channel must be
   owned so the operator uid can connect while other local users cannot. → SS-0.
2. **Secret needs code-signing (F2).** A per-boot secret only improves on a UID
   check if it lives where a same-uid attacker cannot read it. On disk (any mode
   the non-root core can read) a same-uid process reads it too — theatre. The
   secret earns its value only when held in core's memory protected by hardened
   runtime (no `get-task-allow`), which forbids same-uid `task_for_pid`. Thus the
   secret is meaningful **only paired with code-signing** → it is a separate slice.
3. **Skeleton has zero destructive effect (F3).** SH-6's NO-OP skeleton stubs
   every real op. With nothing destructive behind the channel, peercred
   (operator-uid only) + op-enum whitelist is a sufficient boundary for the
   skeleton: a same-uid connection gets only no-op/logged replies. The full secret
   is not required to start. → RED is unblocked on peercred alone.

### 5.2 Decisions (SS-0 … SS-7)

| ID | Sub-design area | Chosen | Stage / note |
|----|-----------------|--------|--------------|
| SS-0 | Socket ownership (F1) | (b) `root:operatorgroup`, mode 0660, manual `bind`/`chmod`/`chown` | Slice 1; → (iii) launchd socket activation (`SockPathOwner`) when plist lands |
| SS-1 | Handoff approach | (E) peercred-authenticated channel + per-boot secret held in-memory (final state) | Slice 1 = peercred only; secret = Slice 2 |
| SS-2 | Secret vs peercred | (c) staged: peercred for skeleton + reversible op (lock); secret MANDATORY for evict/reboot/killall | ⚠️ §8-amendment to SH-5 — see §5.3 |
| SS-3 | Secret generation | (a) shim generates 256-bit CSPRNG (`arc4random_buf`/`SecRandomCopyBytes`) in-memory at load | Slice 2 |
| SS-4 | Secret storage | (a) in-memory both ends, zero disk; handoff carries no on-disk copy | Slice 2; depends on code-signing (F2) |
| SS-5 | Socket creation | (c) manual bind now; launchd socket activation when plist lands | tracks SS-0 / SH-8 |
| SS-6 | Skeleton auth scope | (a) skeleton = socket + peercred + enum whitelist + ping/pong, NO secret | Slice 1 — unblocks RED (F3) |
| SS-7 | Hermetic testing | (a)+(b) injectable credential-source (mock `xucred`) + configurable socket path; (c) manual `-m privileged` tier for real root/launchd | matches SH-7 |

### 5.3 §8-amendment to SH-5 (explicit, not silent)

SH-5 originally locked **(a)+(b)+(c) together** — per-boot secret + `LOCAL_PEERCRED`
+ op enum, all three, from the first slice. SS-2 amends this to a **staged** posture:

- **peercred + op-enum** authenticate the skeleton and reversible ops (lock).
- **the per-boot secret is mandatory** before any destructive op (evict / reboot /
  killall) goes live.

This is a deliberate, recorded correction of a locked decision (mirror of our
discipline: amend in the open, never silently). §8.8's wording — "authenticated via
a per-boot shared secret" — remains the end state; staging only defers the secret to
the slice where it both (a) guards something destructive and (b) can be made real
(F2: code-signing). **No destructive root op ever ships authenticated by peercred
alone.**

### 5.4 Accepted slice order

| Slice | Scope | Auth | Blocks on |
|-------|-------|------|-----------|
| 1 (next RED) | socket + SS-0 ownership + peercred + enum whitelist + ping/pong; all 4 ops = no-op | peercred + enum | — |
| 2 | per-boot secret handshake (auth path becomes real) | + secret | code-signing (F2) |
| 3+ | real ops, one at a time; destructive (evict/reboot) last, once secret is safe | secret for destructive | Slice 2 |

### 5.5 Secret ↔ code-signing dependency (explicit)

The per-boot secret provides defence over peercred **only** when core's memory is
unreadable by same-uid processes — i.e. core is signed with hardened runtime and no
`get-task-allow` entitlement. Until signing infrastructure exists (the same tail
that gates the MIRROR CGEventTap), an in-memory secret is no stronger than peercred.
Therefore Slice 2 — and every destructive op behind it — is gated on code-signing.
The skeleton (Slice 1, peercred) has no such dependency.

---

## 6. Open questions before RED

- **~~Per-boot shared-secret mechanism.~~** RESOLVED at design level (§5, SS-0…SS-7):
  staged — peercred for the skeleton, in-memory secret (paired with code-signing)
  for destructive ops. Implementation lands in Slice 2.
- **Code-signing prerequisite.** LaunchDaemon registration and trust need a signed
  binary — the same tail that gates the MIRROR CGEventTap. Now also gates Slice 2's
  secret (F2 / §5.5). The skeleton (Slice 1) does not depend on it.
- **Login-window operation (§7.11 open Q).** Which modules (if any) must run before
  user login, and does that force more into the LaunchDaemon? Affects how early the
  shim must be available and what it must do pre-login.

---

## 7. Status

Preparation complete. SH-1…SH-12 locked (2026-06-04); scope corrected against §8.8
(4 ops, not 5 modules). Secret-handoff sub-design SS-0…SS-7 locked (2026-06-05),
with SH-5 amended to a staged posture (§5.3) and gap #4 resolved at design level.

**Slice 1 RED is now unblocked** — the NO-OP skeleton stands on peercred alone (F3),
needing neither the secret nor code-signing. Order: Slice 1 (peercred skeleton) →
Slice 2 (secret handshake, gated on code-signing) → Slice 3+ (real ops, destructive
last). Still no code. (MANIFESTO §4: no stubs that pretend; this is a decisions
record, not an implementation.)
