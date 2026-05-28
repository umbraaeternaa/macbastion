# §5.8 PURGE — Secure Erasure (Panic)

Module: `purge`
Codename origin: Purge — total, deliberate, irreversible removal; the last act
Status: **Planned** (eighth and final CHIMERA module, third event-driven defense, only module with ARM64 Assembly)
Target version: chimera v0.9.0
Estimated effort: 5-6 working sessions (~24 hours)

---

## 1. Mission

Operator-triggered (or TETHER-L3-triggered) irreversible destruction of CHIMERA's sensitive state and, optionally, broader operator-designated data.

On Apple Silicon this is primarily **crypto-shredding** — destroying keys so that ciphertext becomes indistinguishable from noise — plus volatile-memory (RAM and cache) zeroing. It is NOT byte-overwriting of flash, which is meaningless on wear-leveled SSDs and would be security theater (MANIFESTO §4).

PURGE is the last resort. When it runs, things end. It must be correct, fast, and honest about exactly what it can and cannot guarantee. It is also the destruction target for TETHER's opt-in L3 tier (§5.7), so it must be specified before either module is implemented.

---

## 2. Why unique

Existing erasure tools on macOS mislead about the hardware reality:

- **`rm`, `srm`, Disk Utility "erase free space"**: `srm` was removed from macOS precisely because overwriting is futile on SSD. These tools, applied to flash, give false confidence — the bytes you "overwrote" may still exist in over-provisioned or wear-leveled blocks.
- **FileVault alone**: encrypts at rest, but its key persists in the Secure Enclave across reboots. FileVault is not a panic button; it does not destroy on demand.
- **The forensic reality everyone ignores**: data in RAM survives briefly after power loss (cold-boot), and keys in the Secure Enclave persist until explicitly evicted.

PURGE differs by being the first panic-erasure tool on macOS that is honest about the SSD and Secure-Enclave reality. It shreds keys (rendering encrypted data unrecoverable instantly, regardless of how flash stores the ciphertext) and zeroes volatile memory — rather than pretending to scrub flash cells it cannot deterministically reach.

---

## 3. What PURGE destroys (tiers)

PURGE operates in ordered tiers. The most sensitive material (keys) dies first, so an interrupted purge has already destroyed the crown jewels before bulk work begins.

| Tier | Scope                                                                 | When        | Speed |
|------|-----------------------------------------------------------------------|-------------|-------|
| 0    | CHIMERA secrets: all CHIMERA Keychain items (VAULT master secrets, TETHER IRK), in-RAM keys of every running module, CHIMERA state DBs (ORACLE baseline, PULSE history, VAULT metadata) | Always      | <1s   |
| 1    | CHIMERA-managed encrypted data: crypto-shred all VAULT key-encryption-keys → every vault blob becomes noise | Default     | Fast  |
| 2    | Operator-designated targets, pre-listed: **crypto-shred only if encrypted**; PURGE REFUSES to "wipe" unencrypted SSD data (see §8) | Opt-in      | Varies|
| 3    | Volatile-memory hygiene: ARM64 `dc zva` cache-line zeroing of sensitive buffers, `explicit_bzero` of all CHIMERA memory regions | Always (last) | Fast |

Default scope is **Tier 0 + Tier 1 only** — CHIMERA's own secrets and vaults. Tier 2 must be explicitly configured by the operator.

---

## 4. Algorithm

On `purge.trigger` with valid authorization (§6):

```
1. EMERGENCY CHOREOGRAPHY (via §6 broker):
   - broadcast purge.imminent to all modules
   - each module: stop work, zero its own in-RAM keys, ack within 500ms
   - any module that does not ack within 500ms is SIGKILLed anyway
2. TIER 0: evict all CHIMERA Keychain items; zero core-held keys
3. TIER 1: destroy VAULT key-encryption-keys (crypto-shred → vaults are noise)
4. TIER 2: process operator-designated targets, IF configured
   - encrypted target: crypto-shred its key
   - unencrypted target: REFUSE; record skipped + reason (see §8)
5. TIER 3: ARM64 dc zva cache-line zero + explicit_bzero sweep of RAM regions
6. (optional, default OFF) write tamper-evident "purged at <ts>" marker
7. (configurable, default REBOOT) power-cycle to clear RAM, or shutdown, or stay-up
```

Keys-first ordering is the core safety property: even if power is cut mid-purge, the key material that makes all encrypted data readable is already gone before any slower bulk operation starts.

---

## 5. Stack

| Component        | Tech                                       | Reason                                              |
|------------------|--------------------------------------------|-----------------------------------------------------|
| Core daemon      | C17                                        | Precise control over memory, syscalls, ordering     |
| Cache/RAM zero   | ARM64 AArch64 Assembly (`dc zva`)          | Canonical fast cache-line zero on Apple Silicon     |
| Secure zeroing   | libsodium (`sodium_memzero`) + `explicit_bzero` | Compiler cannot optimize the wipe away         |
| Keychain         | Security.framework (SecKeychain APIs)      | Evict CHIMERA Keychain items, including Enclave refs |
| Memory location  | Mach VM APIs (`mach_vm_region`, etc.)      | Find CHIMERA memory regions to zero                 |
| IPC with core    | UNIX socket + JSON-RPC 2.0 (per §6)        | Receives trigger, broadcasts purge.imminent         |
| Build system     | clang (C17) + clang ARM64 asm, Makefile    | Asm assembled inline or as `.S`, per CHAFF pattern  |

ARM64 Assembly is justified here because `dc zva` (Data Cache Zero by VA) is the canonical, fastest way to zero cache lines on AArch64, and there is no portable C equivalent with the same guarantees. Per CLAUDE.md §5, every assembly instruction is commented. This is the only module besides CHAFF to touch Assembly, and the only one to use it for erasure.

---

## 6. Authorization — who may trigger

PURGE must never be trivially triggerable. Only three paths are valid:

1. **Operator command** with the master confirmation phrase (`purge.trigger` carrying the phrase).
2. **TETHER L3 escalation** — only if TETHER's L3 is armed (itself opt-in, default disabled; see §5.7).
3. **Physical panic gesture** — configurable, opt-in (e.g. a specific hotkey held N seconds, or a power-button pattern).

Every trigger path is logged — until the log itself is purged. Any `purge.trigger` arriving by any other path, or from a module's capability token that does not grant it, is rejected with `-31007 not authorized` (§6.9). A compromised CHAFF or ORACLE cannot invoke PURGE.

---

## 7. IPC API (per §6 envelope)

### Commands (core → purge)

| Method              | Params                          | Returns                                              |
|---------------------|---------------------------------|------------------------------------------------------|
| `purge.status`      | none                            | `{armed, tiers_enabled, targets_configured, last_test_ts, post_action}` |
| `purge.target.add`  | `{path}`                        | `{targets}` — add a Tier-2 destruction target        |
| `purge.target.remove`| `{path}`                       | `{targets}`                                          |
| `purge.target.list` | none                            | `{targets}`                                          |
| `purge.config.set`  | `{post_action: reboot\|shutdown\|stay, marker: bool}` | `{config}`                       |
| `purge.arm`         | `{confirmation_phrase}`         | `{ok, armed: true}` — make trigger live              |
| `purge.disarm`      | none                            | `{ok, armed: false}`                                 |
| `purge.test`        | none                            | `{report}` — dry-run, lists exactly what WOULD die, destroys nothing |
| `purge.trigger`     | `{authorization}`               | EXECUTE — irreversible (may not survive to return)   |

### Events (purge → core; core relays per §6.6)

| Event                | Payload                                                       |
|----------------------|---------------------------------------------------------------|
| `purge.imminent`     | broadcast before execution — modules zero their own keys      |
| `purge.complete`     | `{tiers_done, targets_skipped, duration_ms}` (if it survives) |
| `purge.test.report`  | `{tier0, tier1, tier2_encrypted, tier2_skipped_unencrypted}`  |
| `purge.error`        | `{code, message, recoverable: bool}`                          |

---

## 8. Security & safety model

### Protects against
- Data falling into hostile hands after seizure or coercion: keys gone means all CHIMERA-encrypted data is indistinguishable from noise, instantly, regardless of SSD flash behavior
- Forensic recovery of CHIMERA secrets: Keychain items evicted, in-RAM keys zeroed
- Cold-boot key extraction: RAM zeroed in Tier 3, and the default reboot power-cycles memory

### Explicitly does NOT protect against (honest)
- Recovery of data already copied OFF the machine before purge ran
- SSD physical forensics of UNENCRYPTED data — TRIM is best-effort and flash may retain blocks. This is exactly why PURGE REFUSES to pretend-wipe unencrypted Tier-2 targets (see invariant below). Only crypto-shredding of encrypted data is reliable.
- An adversary who imaged the disk BEFORE purge ran
- Secure Enclave hardware extraction by a nation-state-class actor
- Power interrupted mid-purge — mitigated, not eliminated, by keys-first ordering

### Safety invariants
- **Irreversible by design.** `purge.trigger` has no undo, no recovery. That is the point.
- **Honest wipe only.** PURGE crypto-shreds encrypted data. It REFUSES to "securely wipe" unencrypted SSD data, because it cannot guarantee that on wear-leveled flash. For unencrypted Tier-2 targets it records them as skipped with the reason, and the guidance is: encrypt it first, then PURGE can shred the key. No security theater (MANIFESTO §4).
- **Mandatory test before arming.** `purge.test` is a dry-run that lists exactly what would be destroyed and destroys nothing. The operator must see this before `purge.arm`.
- **Tier 2 is opt-in and explicit.** Operator data is never destroyed implicitly; only pre-listed targets are touched.
- **Default scope is Tier 0+1.** Without configuration, PURGE destroys only CHIMERA's own secrets and vaults.
- **No automatic trigger except TETHER L3**, which is itself opt-in and default-disabled.
- **No final countdown on TETHER L3.** When L3 fires after its full ladder (~6.5 min of confirmed absence), PURGE executes without an additional audible countdown — a loud countdown in a hostile environment would signal an adversary to physically intervene. The cancellation window was the entire TETHER ladder.

### Threat model assumptions
- Adversary cannot inject IPC into core to forge a trigger (capability tokens, §6.9)
- Crypto-shredding is sound: destroying the key renders AES-256-GCM ciphertext unrecoverable
- The operator has encrypted anything they truly need destroyed (else PURGE honestly cannot guarantee it)

---

## 9. Open questions

These need decisions before implementation begins:

- **Post-purge default revisited per environment.** Reboot clears RAM but announces that something happened; stay-up is stealthier but RAM residue lingers; shutdown ends the session. Default is reboot — is that right for the primary threat model, or should first-run setup ask?
- **Tamper-evident marker policy.** Default is no marker (deniability). Should the opt-in marker be cryptographically signed (provable to the operator) or a plain timestamp?
- **Verifiable point-of-no-return.** Keys-first ordering means the crown jewels die first, but can we expose a verifiable signal "Tier 0 complete" so the operator (or an interrupted-run forensic check) knows the irreversible threshold was crossed?
- **Panic gesture design.** What physical trigger is reliable under stress yet not accidentally activatable? Hotkey-hold? Power-button pattern? Both behind `purge.arm`?
- **Module ack timeout.** 500ms for modules to zero their keys before SIGKILL — too short for a busy ORACLE mid-inference? Tune per module, or hold one global value?
- **Enclave eviction completeness.** How thoroughly can userspace guarantee a Secure Enclave key is evicted vs merely dereferenced? Document the real guarantee, not the hoped-for one.

To be resolved during implementation.

---

## 10. Status

**Planned.** No code yet.

Depends on:
- Core orchestrator with IPC infrastructure (§6, complete)
- Keychain access and Mach VM access from core
- libsodium in the chimera build environment

PURGE is the destruction target for TETHER L3 (§5.7), so it must be specified — and ultimately implemented — before either module's destructive path is wired.

Completing this specification closes Part 2 (§5): all eight CHIMERA modules are now specified. The event-driven layer (VAULT, TETHER, PURGE) is fully defined. What remains for ARCHITECTURE.md is §7 (module lifecycle, Part 4) and §8 (security model, Part 5).

No imitations. No stubs. (See MANIFESTO §4.)
