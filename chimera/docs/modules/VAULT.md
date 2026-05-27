# §5.6 VAULT — Time-Locked Storage

Module: `vault`
Codename origin: Vault — physical safe whose lock responds not just to a key, but to the world around it (time, presence, state)
Status: **Planned** (sixth CHIMERA module, first event-driven defense)
Target version: chimera v0.7.0
Estimated effort: 5-6 working sessions (~22 hours)

---

## 1. Mission

Encrypted file storage whose decryption key materializes only when the operator's pre-declared policy is satisfied. Files cannot be opened by accident, by stress, by coercion at 3am, or by a malicious process that gained read access while the operator is offline.

VAULT is the first event-driven module: previous modules (CHAFF, ECHO, ORACLE, MIRROR, PULSE) are always-on defenses. VAULT does nothing until the operator runs `vault.unlock` — and then it does nothing unless the world is in the right state.

The goal is to make irreversible disclosure (leak, share, send, copy) require the operator to be in the right place, at the right time, in the right cognitive state. Anything less, and the key simply does not exist.

---

## 2. Why unique

The encrypted-storage landscape currently splits into four camps, none sufficient:

- **OS full-disk encryption** (macOS FileVault, BitLocker): protects against a stolen laptop, but every process the user runs can read everything the user can. No temporal or contextual gating.
- **Password-based vaults** (VeraCrypt, Cryptomator, Keychain): the password works at any time. Operator under coercion + correct password = files compromised. No protection against the operator's own future bad decisions.
- **Cloud vaults** (1Password vault, iCloud Advanced Data Protection): stream metadata to vendor, key recovery exists by design, files leave the machine.
- **Hardware tokens** (YubiKey, Secure Enclave on its own): require presence, not state. Token plugged in = vault unlockable regardless of time, fatigue, or context.

VAULT differs by combining four properties no existing tool has together:

1. **State-gated, not key-gated.** The decryption key is derived from the *result* of a policy evaluation. If the policy denies, no key exists anywhere — not in RAM, not in Keychain, not in Secure Enclave.
2. **Local-only and machine-bound.** Master key lives in macOS Keychain protected by Secure Enclave. Vault files cannot be opened on another machine, even with the operator present. This is intentional (MANIFESTO §1: one machine, one owner).
3. **Module-aware policy.** Policies can require `pulse_mode == normal`, `tether == present`, `network_ssid == "MyHomeWifi"`, `seconds_since_boot < 300`. VAULT becomes one organ in the larger CHIMERA organism.
4. **Coercion-resistant by design.** Reboot-required policies impose physical wait time on adversaries. Cognitive-state policies impose biological wait time. Network policies impose geographical wait time.

This is the first time/state-policy locked storage on macOS, open-source or otherwise.

---

## 3. Algorithm

### Vault structure on disk

Each vault is a self-contained directory under `~/.config/chimera/vault/`:

  <vault_id>/
    metadata.json       — vault_id (uuid), name, created_at, policy_hash
    policy.dsl          — operator-authored policy (plaintext, hashed into key)
    ciphertext.bin      — AES-256-GCM encrypted blob (the actual files)
    audit.log           — append-only log of unlock attempts

The master encryption key is NEVER stored. It is derived at unlock time from:

  derived_key = Argon2id(
      keychain_master_secret +     # from Secure Enclave, per-vault
      sha256(policy.dsl) +         # binds key to current policy
      context_salt                 # rotated per unlock
  )

Editing `policy.dsl` externally changes its hash, which invalidates the key. Policy must be modified via `vault.policy.update`, which re-encrypts under the new hash.

### Unlock flow

When the operator runs `vault.unlock <vault_id>`:

  1. Load policy.dsl for vault_id
  2. Gather current context:
     - wall-clock time (UTC + local)
     - day of week, day of month
     - PULSE mode (if PULSE running; "unknown" if not)
     - TETHER status (if TETHER running; "unknown" if not)
     - boot time (seconds since last reboot, via sysctl kern.boottime)
     - active network (SSID or "none")
     - ORACLE anomaly score (if ORACLE running)
  3. Evaluate policy against context → ALLOW | DENY | DEFER(seconds)
  4. On ALLOW:
     - Request keychain_master_secret from macOS Keychain (Secure Enclave)
     - Compute derived_key (Argon2id)
     - Decrypt ciphertext.bin into RAM
     - mount_tmpfs at /tmp/chimera-vault-<random_16_bytes>
     - Write plaintext files to tmpfs
     - explicit_bzero the in-RAM plaintext copy
     - Schedule auto-relock via kqueue timer (default 15 min)
     - Schedule kqueue watch on mount path (any external ls/stat → relock)
     - Schedule kqueue watch on policy variables (any condition break → relock)
     - emit vault.unlocked event
  5. On DENY:
     - Append to audit.log (timestamp, reason, sanitized context)
     - emit vault.denied event
     - return reason to caller
  6. On DEFER:
     - Append to audit.log
     - emit vault.denied event with defer_seconds
     - return wait time to caller

### Concurrent unlock policy

**Only ONE vault may be unlocked at any time.** Attempting `vault.unlock` while another vault is open returns `denied: another_vault_open` and names which vault. The operator must explicitly `vault.lock` the open one first. This is a deliberate constraint (MANIFESTO §4): the blast radius of a memory dump is bounded.

### Re-lock triggers

Auto-relock fires on any of:
  - relock timer expiry (per-vault, default 15 min)
  - policy condition change (e.g. tether broke, pulse_mode shifted to tired)
  - tmpfs mount path was accessed by a process other than the unlocking caller
  - macOS shutdown or sleep signal
  - explicit `vault.lock` IPC call

Re-lock procedure:
  - unmount tmpfs (zeros tmpfs pages by definition)
  - explicit_bzero the in-RAM derived_key
  - explicit_bzero any cached context_salt
  - emit vault.locked event with reason

---

## 4. Policy DSL

VAULT uses a **simplified declarative DSL** — not Lua, not Python, not embedded scripting. Whitelisted predicates only, parsed by VAULT's own evaluator.

### Grammar (informal)

  policy       := allow_block relock_block?
  allow_block  := "allow_when:" expression
  relock_block := "relock_after:" duration
  expression   := predicate (("and" | "or") predicate)*
                | "not" expression
                | "(" expression ")"
  predicate    := variable operator value
  variable     := hour | weekday | day_of_month | pulse_mode | tether
                | network_ssid | seconds_since_boot | oracle_score
  operator     := "==" | "!=" | "in" | "between" | "<" | "<=" | ">" | ">="
  duration     := <number> ("min" | "hour")

No function calls. No loops. No variable assignment. No reflection. The evaluator is ~200 lines of C and fully auditable.

### Examples

  # Business-hours vault for tax documents
  allow_when:
    weekday in [mon, tue, wed, thu, fri]
    and hour between 09 and 17
    and pulse_mode in [normal, caution]
    and tether == present
  relock_after: 30min

  # Personal journal, home evenings only
  allow_when:
    network_ssid == "MyHomeWifi"
    and hour between 20 and 23
  relock_after: 60min

  # Cold-storage vault: only within 5 min of fresh reboot
  # Forces adversary to physically reboot, buying time and triggering alerts
  allow_when:
    seconds_since_boot < 300
    and pulse_mode == normal
  relock_after: 10min

  # Maximum-coercion-resistance vault
  allow_when:
    seconds_since_boot < 300
    and weekday in [sat, sun]
    and hour between 10 and 16
    and tether == present
    and pulse_mode == normal
  relock_after: 15min

### Fail-closed default

If a policy references a variable from a module that is not currently running (e.g. `pulse_mode` but PULSE daemon is off), the evaluator returns DENY. To explicitly opt out of a check, operator writes `pulse_mode in [normal, caution, tired, exhausted, unknown]`.

---

## 5. Stack

| Component       | Tech                                       | Reason                                            |
|-----------------|--------------------------------------------|---------------------------------------------------|
| Core daemon     | C17 (vaultd)                               | Crypto and memory hygiene need precise control    |
| Crypto          | libsodium                                  | AES-256-GCM, Argon2id, secure memory, audited     |
| Master key      | macOS Keychain + Secure Enclave            | Hardware-backed, never exposed to userspace       |
| Policy parser   | Hand-written recursive-descent in C        | ~200 lines, no Lua/Python deps, fully auditable   |
| Mount           | mount_tmpfs (macOS-native)                 | RAM-backed, zeroes on unmount, no FUSE            |
| Memory hygiene  | mlock + explicit_bzero                     | Prevents swap-out and ensures wipe                |
| IPC with core   | UNIX socket + JSON-RPC 2.0                 | Same protocol as previous modules                 |
| Watches/timers  | kqueue (EVFILT_TIMER, EVFILT_VNODE)        | Event-driven relock, no polling                   |

**Why libsodium, not OpenSSL/BoringSSL:** smaller surface area, opinionated defaults, well-audited primitives. AES-256-GCM and Argon2id are the only primitives we need; libsodium gives both safely.

**Why custom DSL parser, not Lua:** policies must be readable and auditable by humans who do not know Lua. A whitelisted grammar makes it impossible to accidentally write `allow_when: true` or smuggle a backdoor through a clever lambda.

**Why tmpfs, not FUSE:** FUSE adds a userspace process between vault and apps — another attack surface and another memory copy. tmpfs is kernel-resident, supported natively on macOS, and unmount guarantees page zeroing.

---

## 6. IPC API

### Commands (core → vault)

| Method                    | Params                                       | Returns                                              |
|---------------------------|----------------------------------------------|------------------------------------------------------|
| `vault.create`            | `{name, policy_dsl}`                         | `{vault_id}`                                         |
| `vault.list`              | none                                         | `[{vault_id, name, last_unlock, policy_summary}]`    |
| `vault.unlock`            | `{vault_id}`                                 | `{ok, mount_path, relock_in_sec}` / `{denied, reason}` / `{defer, seconds}` |
| `vault.lock`              | `{vault_id}`                                 | `{ok, reason}`                                       |
| `vault.policy.update`     | `{vault_id, new_policy_dsl}` (must be unlocked first) | `{ok, new_policy_hash}`                      |
| `vault.add_file`          | `{vault_id, source_path}` (must be unlocked) | `{ok, added_path}`                                   |
| `vault.delete`            | `{vault_id, confirm: master_phrase}`         | `{ok}`                                               |
| `vault.audit`             | `{vault_id, limit}`                          | `[audit_entries]`                                    |
| `vault.status`            | none                                         | `{currently_unlocked: vault_id or null, ...}`        |

### Events (vault → core)

| Event                       | Payload                                                                  |
|-----------------------------|--------------------------------------------------------------------------|
| `vault.unlocked`            | `{vault_id, mount_path, policy_context_summary, relock_at_utc}`          |
| `vault.locked`              | `{vault_id, reason: timer|policy_break|external_access|shutdown|manual}` |
| `vault.denied`              | `{vault_id, reason, defer_seconds: number or null}`                      |
| `vault.condition.change`    | `{vault_id, variable_changed, new_value}` (only while unlocked)          |
| `vault.tamper`              | `{vault_id, evidence}` if ciphertext integrity (GCM tag) fails           |
| `vault.error`               | `{code, message, recoverable: bool}`                                     |

---

## 7. Dependencies

System:
- macOS 14+
- macOS Keychain access (per-vault Keychain item, Secure Enclave protected)
- `libsodium` (`brew install libsodium`)
- `mount_tmpfs` (system-shipped)
- ~5 MB binary, ~20 MB RAM per unlocked vault (plus vault content size)

Module integrations (optional but recommended):
- PULSE — for `pulse_mode` policy variable
- TETHER — for `tether` policy variable
- ORACLE — for `oracle_score` policy variable
- MIRROR — not used (input layer is irrelevant to storage policy)

If a referenced module is not running and the policy variable lacks an explicit `or unknown` clause, evaluation fails closed (DENY).

Project-internal:
- `~/.config/chimera/vault/<vault_id>/` — per-vault directory (mode 0700)
- Per-vault Keychain item, label `chimera-vault-<vault_id>`
- IPC socket via core (no direct sockets)
- Vault files excluded from Time Machine and iCloud sync via `xattr com.apple.metadata:com_apple_backup_excludeItem`

Network: VAULT makes NO outbound network calls. Pure local module.

---

## 8. Security model

### Protects against
- Accidental opening of high-stakes files in the wrong mood, time, or place
- Process-level read attacks: while locked, even the operator's other processes cannot read vault contents — the key does not exist anywhere
- 3am cascade disclosures: policies can require `pulse_mode == normal`
- Coercion: reboot-required policies impose physical wait; tether-required policies impose locational constraint
- Cloud sync leakage: vault files explicitly excluded from iCloud, Time Machine, Dropbox
- Tampering: AES-256-GCM AEAD; any modification produces `vault.tamper` event on next unlock attempt

### Does NOT protect against
- A deliberately permissive policy authored by the operator
- $5 wrench attack with hours of patience: eventually the world will match the policy
- Compromised Secure Enclave (out of scope; OS-trust boundary)
- Memory snapshot while vault is unlocked: the derived key and plaintext exist in RAM for the duration of the unlock window
- Operator opening vault, then taking screenshots / sending files / copying to non-vault locations (post-decryption is out of scope; that is the MIRROR/PULSE/operator-discipline layer)
- Adversary with full machine root + Secure Enclave bypass (assumes nation-state actor or hardware extraction)

### Cryptographic invariants
- AES-256-GCM provides confidentiality + integrity
- Argon2id provides key derivation (memory-hard, brute-force resistant)
- Policy hash is bound into the key derivation — modifying policy.dsl externally invalidates all existing ciphertext for that vault
- Per-vault master secret in Secure Enclave is non-extractable

### Privacy invariant
VAULT audit logs record ONLY:
- vault_id
- timestamp_utc
- decision (ALLOW / DENY / DEFER)
- reason string (e.g. "hour_out_of_range", "tether_absent")
- sanitized context (variable names, NOT values; e.g. "pulse_mode_required_normal_got_tired", but not the operator's current SSID)

VAULT NEVER logs:
- file contents
- file names inside the vault
- raw policy variable values (current SSID, current pulse score, etc.)
- mount path contents

### Recovery invariant
**There is no recovery path.** If the operator forgets the master phrase used during `vault.create`, the data is gone forever. No Shamir secret sharing, no escrow, no backdoor. This is intentional (MANIFESTO §1: one operator). Operators who need backups must export plaintext during an unlock window to a separately encrypted offline medium.

---

## 9. Open questions

These need decisions before implementation begins:

- **Master phrase strength enforcement.** Should `vault.create` reject weak phrases (e.g. < 12 chars, dictionary words)? Or trust the operator?
- **Per-vault Keychain item visibility.** macOS Keychain entries are visible in Keychain Access.app. Should we use a separate keychain file (`~/.config/chimera/vault.keychain`) to keep vault keys out of the default login keychain UI?
- **Mount path randomness.** 16-byte random suffix is good enough, but `/tmp/chimera-vault-*` glob still reveals "a vault is open". Use entirely random prefix like `/tmp/<32-byte-random>`?
- **kqueue mount-path watch reliability.** EVFILT_VNODE on a tmpfs mount works in practice on macOS 14+, but undocumented edges exist. Fallback: poll readdir every 1s?
- **Policy update during unlock.** `vault.policy.update` requires unlock, re-encrypts under new policy hash. What if the new policy would not allow the current context? Reject update? Allow with warning?
- **Vault visibility in `vault.list` when locked.** Should vault names be visible while locked, or only vault_ids? Trade-off: usability vs metadata leakage if disk is seized.
- **Per-vault relock-on-screen-lock.** Should every vault auto-relock when macOS screen locks, regardless of timer? Sensible default but breaks workflows like long downloads from a vault.

To be resolved during implementation.

---

## 10. Status

**Planned.** No code yet.

Depends on:
- Core orchestrator with IPC infrastructure
- Keychain access flow from core (entitlements, user-facing prompt on first vault.create)
- PULSE (preferred, for `pulse_mode` predicate)
- TETHER (preferred, for `tether` predicate)
- libsodium installed in the chimera build environment

After VAULT works, CHIMERA crosses from continuous defenses (CHAFF, ECHO, ORACLE, MIRROR, PULSE) into event-driven safeguards. The remaining two modules (TETHER, PURGE) extend this event-driven layer: TETHER reacts to physical proximity, PURGE reacts to operator-initiated panic.

No imitations. No stubs. (See MANIFESTO §4.)
