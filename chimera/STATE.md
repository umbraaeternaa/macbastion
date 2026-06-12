# CHIMERA — Project State Snapshot

> Updated: 2026-06-08
> Version: 0.1.0-alpha (genesis)

---

## Completed module specifications

| Module | Lang  | Commit    | Notes                           |
|--------|-------|-----------|---------------------------------|
| CHAFF  | C     | `e0c8116` | §5.1 — background traffic gen   |
| ECHO   | C     | `a64f7d9` | §5.2                            |
| ORACLE | Py    | `2f753cb` | §5.3 — local LLM anomaly detect |
| MIRROR | C     | `a951c92` | §5.4 — behavioral noise inject  |
| PULSE  | C+Py  | `5f5b64a` | §5.5 — cognitive load monitor   |
| VAULT  | C     | `1fdc517` | §5.6 — time-locked storage      |
| TETHER | C++   | `3b5fca9` | §5.7 — proximity dead-man       |
| PURGE  | C+Asm | `4a3c9df` | §5.8 — secure erasure (panic)   |

All 8 of 8 module specifications complete. Part 2 (§5) closed.

Genesis commit (manifesto + architecture Part 1): `f229751`

## Completed design records

| Record             | Commit    | Notes                                                                                                      |
|--------------------|-----------|------------------------------------------------------------------------------------------------------------|
| UX                 | `cb10247` | UX surface decision — CLI + swiftbar + event stream (`chimera/docs/UX.md`)                                 |
| OPSEC              | `a3ae3ad` | Operator security discipline — companion to §8 (`chimera/docs/OPSEC.md`)                                   |
| SHIM               | `7092f8e` | Privileged shim decisions SH-1…12 + secret-handoff SS-0…7 + SH-5 staged amendment (`chimera/docs/SHIM.md`) |
| ORACLE_EXPLAIN     | `ea10e5e` | Explainability design EP-1…9 (`chimera/docs/ORACLE_EXPLAIN.md`)                                            |
| ORACLE_TIMEMACHINE | `e1c3cbc` | Time-machine design TM-1…11 (`chimera/docs/ORACLE_TIMEMACHINE.md`)                                         |

---

## ARCHITECTURE.md progress

Last completed section: **§8** (Part 5 of 5). Part 1 (§1–§4) also complete.

Done:

- §5 — Detailed module specs (Part 2) — **DONE** (8/8: `4a3c9df` closes it)
- §6 — IPC protocol: JSON-RPC schemas (Part 3) — **DONE** (`3daa138`)
- §7 — Module lifecycle (Part 4) — **DONE** (`1863057`)
- §8 — Security model (Part 5) — **DONE** (`52477fe`)

---

## Specification phase: COMPLETE

As of 2026-05-28, the CHIMERA specification phase is closed. §8 closes it:
the architectural document is whole and authoritative. No spec work remains.

- **ARCHITECTURE.md** — all five parts: §1–§4 (concept, stack, principles),
  §5 (modules), §6 (IPC), §7 (lifecycle), §8 (security model)
- **Module specs** — 8 of 8 (CHAFF, ECHO, ORACLE, MIRROR, PULSE, VAULT, TETHER, PURGE)
- **7 design documents total** — 5 ARCHITECTURE parts + UX.md + OPSEC.md

**Next — code phase begins:**

- Core skeleton, targeted at chimera **v0.2.0** — socket server, router, broker,
  registry, capability-token issuer, privileged shim

---

## Code status

Code phase: all 8 core modules implemented (ETAP 2 closed). ETAP 3 underway —
Step 0 (CHAFF spec align), Step 1A (config request_timeout_s), Step 1B
(Router 4A), Step 2 (CHAFF: 2A bootstrap, 2B RED, 2C GREEN, 2D daemon + integration),
MIRROR (bootstrap, RED, engine GREEN, daemon wiring), ORACLE (RED, observe-first
GREEN, Mode B GREEN, explainability GREEN, time-machine GREEN) done. Privileged
shim (trust-plane, NOT an organ): Slice 1 NO-OP skeleton (RED→GREEN) done. TETHER
(native module, §5.7): Slice 1 engine (RED→GREEN) + daemon-wiring (RED→GREEN) +
Slice 3A react-entrypoint (RED→GREEN) done. CORE: idea #3 Slice 3B anomaly-relay
(RED→GREEN) done — a NEW core capability. ORACLE: idea #3 Slice 3C anomaly-emit
(RED→GREEN) done — the real producer. **Idea #3 (Anomaly-Tripwire) COMPLETE** —
3A+3B+3C wired + e2e-confirmed by 3D.
Last completed: **PULSE IdleTracker — the idle sub-signal goes live (PD-idle-1)** (commit `2d7517f`, Day 18).
PULSE's temporal signal already runs live, but `temporal_signal(..., last_idle_end=None)` hardcoded None — the
idle sub-signal was dead (only hour-of-day + session contributed). New pure/hermetic `pulse/idle.py`
`IdleTracker` derives `last_idle_end` from a stream of `(now, idle_seconds)`: idle past `IDLE_GAP_THRESHOLD_S`
(5 min) opens a gap; falling back below it closes the gap (operator returned) and stamps `last_idle_end = now`.
The heart of group-B's live idle producer. 5 RED->GREEN. 1028 -> 1033. mypy --strict + ruff clean.
NEXT (PD-idle-2): the real `ioreg -c IOHIDSystem` HIDIdleTime read behind a seam (manual-tier) + wire the
tracker into the daemon (`client.py`: feed each tick, pass `last_idle_end=tracker.last_idle_end` instead of None).

Prior milestone: **`chimera audit --failures` CLI flag — failures filter, locally** (AD-5; commit `51056f7`,
Day 17). The local `chimera audit` CLI (reads `audit.jsonl` off disk, works even when core is down) now takes
`--failures`, passing `failures_only` through to `AuditLog.recent`. Closes the CLI<->RPC symmetry: an operator
can ask "did any reflex fail?" from the terminal, not only a connected client over `core.audit`. Live-verified
end-to-end (`--failures` shows only the error entry). 2 RED->GREEN (10 cli tests). 1026 -> 1028. mypy
--strict + ruff clean. The audit trail is now COMPLETE: append-only, capped, queryable over socket + CLI,
failure-aware.
NEXT: a big arc (signing / click-key / PULSE) fresh; or close Day 17 with `/check` + `/handoff`.

Prior milestone: **`core.audit` failures-only filter — "did any reflex fail?"** (AD-4; commit `5bef38c`,
Day 17). `AuditLog.recent` gains `failures_only=True` (keep only `outcome != "ok"`); it scans the whole
capped trail before taking the last n, so a failure isn't missed just because successful actuations followed.
`core.audit` passes a `failures_only` request param through. Turns the trail from a log into a diagnosis tool:
an operator/surface can ask the core directly whether any autonomous reflex failed (module offline, shim
unavailable). Unfiltered path unchanged. 2 RED->GREEN (8 audit + 5 core.audit tests). 1024 -> 1026. mypy
--strict + ruff clean. NEXT: small hardens (swiftbar wiring of `core.audit`; `chimera audit --failures` CLI
flag) or a big arc (signing / click-key / PULSE) fresh.

Prior milestone: **`core.audit` RPC — the reflex trail over the socket** (AD-3; commit `c8594a4`, Day 17).
The audit trail was readable only via the local file-reading `chimera audit` CLI. `core.audit` (a core method,
auto-advertised to surfaces via `CORE_METHODS`) now returns `{entries: [...]}` — the last `n` actuations
(optional `n`, default 50) in chronological order — so connected clients (swiftbar, remote tools) can query it
through the same JSON-RPC surface as `core.status` et al. Handler reads `self._audit_log.recent(n)`; `n`
validated. 3 RED->GREEN (649 default). 1021 -> 1024. mypy --strict + ruff clean. NEXT: small hardens (reactive
cooldown/debounce; swiftbar wiring of `core.audit`) or a big arc (signing / click-key / PULSE) fresh.

Prior milestone: **audit-trail rotation cap — the trail can't grow without bound** (AD-2; commit `3461b99`,
Day 17). `AuditLog` gains a `max_entries` cap (default 1000; injectable for tests); after each append `_trim()`
rewrites the file to the last N lines (0600 preserved), so a long-running daemon's `audit.jsonl` can't fill
the disk over months. Server's always-on AuditLog uses the default 1000 unchanged. 1 RED->GREEN (7 audit
tests). 1020 -> 1021. mypy --strict + ruff clean. NEXT: a `chimera audit` count/`-n` is already there; small
hardens (e.g. `core.audit` RPC for remote surfaces) or a big arc (signing / click-key / PULSE) fresh.

Prior milestone: **MIRROR slice 3 — secure-field downgrade (never jitter password fields)** (AX-3; commit
`b987baf`, Day 17). MIRROR is now SAFE to actually run. New pure/testable `mirror_tick_params(rt, is_secure)`
-> the active profile downgraded to light (`profile_downgrade`) when a secure field is focused, so the
injector never perturbs sensitive input. New secure-field probe seam (`mirror_set_secure_field_check`); real
backend (manual-tier — Accessibility) inspects the system-wide focused AXUIElement, true iff its subrole ==
`AXSecureTextField`. The injector loop now ticks via `mirror_tick_params(rt, g_secure_field_check())` (the
focused field is queried outside the runtime lock). 1 RED->GREEN (45 MIRROR Unity). 1019 -> 1020. `-Werror`
clean. NEXT (MIRROR arc): click/key jitter; or pause MIRROR (core proven + safe) for the code-signing arc /
another organ.

Prior milestone: **MIRROR arc slice 2 — `mirror.enable` starts a REAL CGEvent input injector** (AX-2;
commit `9a05af3`, Day 17). Slice 1 probed Accessibility and reported an honest reason; with Accessibility
granted it still returned a `code_signing` wall. Slice 2 makes enable **go live**: new injector seam
(`mirror_set_injector`; tests inject a stub). Accessibility granted -> `rt->enabled = 1`, start the injector
via the seam, return `ok` (roll back + "injector failed" error if it can't start). **Design call:**
code-signing is a DISTRIBUTION concern, not a local-use blocker — a power-user who grants Accessibility can
post events, so the signing gate is dropped for local use (CHIMERA is a power tool, not a mass product).
Real injector backend (MANUAL-TIER — not unit-tested, needs a live Accessibility grant): a pthread that
while enabled posts small humanlike mouse-move perturbations (`perturb_mouse` scaled by the profile's
`mouse_sigma`) via `CGEventCreateMouseEvent` + `CGEventPost`, jittered gap via `perturb_timing`; stops when
`mirror.disable` clears `enabled`. Dispatch holds the runtime mutex so the thread can't see a half-state.
Test replaced (`reports_signing` -> `starts_injector`); 44 MIRROR Unity, count unchanged at 1019. `-Werror`
clean.
✅ **LIVE-VERIFIED on real hardware** (Day 17, throwaway harness): forced the probe granted, enabled, ran the
injector 6s — **the cursor visibly jittered when run from Terminal.app** (which holds Accessibility), and did
NOT move when run from VS Code's terminal (Code.app lacks the grant). Same binary, different responsible app
-> a clean demonstration of TCC's per-app model. `CGEventPost` + `perturb_mouse` + the loop genuinely move
the cursor with permission; `mirror.disable` stops it. MIRROR's core capability (behavioral-noise injection)
is PROVEN on hardware. NEXT (MIRROR arc): secure-field downgrade wiring (force light on password fields) +
click/key jitter; production needs code-signing for a STABLE/grantable Accessibility identity (signing arc).

Prior milestone: **MIRROR arc slice 1 — `mirror.enable` does a REAL Accessibility probe** (AX-1; commit
`0087170`) — `AXIsProcessTrusted()` behind an injectable seam; honest probe-driven errors.

Prior milestone: **reflex audit trail — COMPLETE: readable surface + full coverage** (AD-1; commits `a64ee7d`
`chimera audit` CLI + `6465ed5` shim-tail audit). The audit trail is now end-to-end usable. New
`render_audit(entries)` -> readable lines (local time, firing topic -> command(s), `[outcome]`); new
**`chimera audit [-n N]`** subcommand reads `audit.jsonl` straight off disk (no core socket — works even when
core is down) and prints the trail — the **fourth operator surface** beside status/watch. And the shim-driven
escalations that bypass `_relay_one` are now audited directly: L1 `shim.lock` -> ok / error / "shim
unavailable"; L3 -> "refused: L3 opt-in only" (a requested-but-refused PURGE is security-relevant and MUST
leave a trace). **The audit trail now covers EVERY reflex core actuates.** Live-smoked against the real CLI.
8 RED->GREEN (4 render + 2 subcommand + 2 shim audit). 1009 -> 1017. mypy --strict + ruff clean.

Prior milestone: **reflex audit trail foundation** (commits `9d733b7` store + `ee7fafb` wiring) — `AuditLog`
append-only JSONL (0600/0700, corrupt line skipped), wired into `_relay_one` (always on); the accountability
record of WHAT core actuated, WHEN, OUTCOME. The four operator surfaces are now: `status`, `watch`, `audit`
(CLI) + swiftbar (parent-scope, out of chimera).

Prior milestone: **ORACLE all-clear — the threat axis is now bidirectional** (commit `65bf8db`) — crossed
1000 tests; `_handle_classify` emits `oracle.anomaly.cleared` on the downward cross below `threshold -
ANOMALY_HYSTERESIS` (0.1); core stands obfuscation down on the matching axis.

Prior milestone: **de-escalation — tether.recovered stands down the obfuscation organs** (commit `f51bdf0`)
— first stand-down; `tether.recovered -> [chaff.generation.stop, echo.stop]`; the reflex web goes down, not
only up; vault stays locked (no auto-unlock).

Prior milestone: **anomaly also starts ECHO timing normalization** (commit `5cfe243`) — both obfuscation
organs (CHAFF volume + ECHO timing) fire on threat; MIRROR deferred (mirror.enable gated behind unbuilt
signing + Accessibility infra — surfaced honestly).

Prior milestone: **anomaly also turns on CHAFF decoy traffic** (commit `837a739`) — first active
countermeasure; `chaff.generation.start` in the anomaly fan-out.

Prior milestone: **`chimera watch` — live event stream of the organism** (commit `46056c6`); third UX
surface — `render_event` + `chimera watch` subscribe `events.sock` and print critical events live. The third UX
surface (UX.md). New `render_event(topic, payload)` -> a concise operator line per pushed event (friendly
summaries for tether.absent / escalation / recovered, pulse.mode.changed, oracle.anomaly.detected,
purge.imminent, vault.*; raw fallback). New `chimera watch` subcommand subscribes to the critical topics on
`events.sock` (`core.subscribe`) and prints each Notification as it fires; core down -> friendly + exit 1.
Reuses the existing broker + events.sock push infra. Now the operator/client SEES reflexes fire live (walk
away -> "TETHER: paired device absent" then "VAULT: locked" scroll past). 5 RED->GREEN + 1 integration
(live subscribe->publish->print). 988 -> 994. mypy --strict + ruff clean. The operator surface trio
(status snapshot + watch stream; swiftbar is parent-scope) is in place. NEXT: a new capability, harden, or
the swiftbar surface (needs explicit OK — parent macbastion).

Prior milestone: **`chimera status` shows live VAULT state — the organism view is complete** (commit
`7cc7877`). `_status` now also queries `vault.status` (routed to the daemon, folded in as
`{available, open, open_vault_id}`; offline/erroring -> shown offline, never a stack trace; socket
round-trip refactored into `_fetch`, reused for both calls); `render_status` prints a
`VAULT: open (id) / locked / offline` line. `chimera status` renders the FULL live organism: core +
modules + PULSE cognitive mode + armed reflexes + whether the vault is open right now — the complete demo
picture (research §4). 3 RED->GREEN render + integration. 985 -> 988. mypy --strict + ruff clean. NEXT: a
swiftbar passive surface (touches parent macbastion — needs explicit OK), richer status, or a new slice.

Prior milestone: **`chimera status` surfaces the reactive state** (commit `00638d6`) — `core.status` gained
a `reactive` section (live PULSE mode + armed reflexes); `render_status` prints them. 5 RED->GREEN.

Prior milestone: **`chimera status` — operator status-view** (commit `6e06ca5`); first operator-facing
surface (UX.md CLI). `core/status_view.py` `render_status()` renders the `core.status` payload; the
`chimera status` subcommand fetches + prints it (graceful when core is down). 6 RED->GREEN + 1 integration.

Prior milestone: **core actuates TETHER's escalation ladder — the dead-man's graduated teeth** (commit
`ea3c9c0`). TETHER is EMIT-ONLY by design (the Monitor only REQUESTS — spec §8 safety); core now
subscribes to `tether.escalation` (`_escalation_loop` / `_on_tether_escalation`) and honours the requested
action per stage: **L1 `lock_screen` -> `shim.lock`** (physically lock the Mac via the privileged shim);
**L2 `lock_vaults` -> `vault.lock`**; **L3 `trigger_purge` -> NEVER auto-run** (irreversible; PURGE stays
operator opt-in via `core.purge`, only logged). Each action isolated. Graduated dead-man: brief absence ->
screen, longer -> vaults, longest -> (opt-in) PURGE. 3 RED->GREEN (603 default). 970 -> 973. mypy --strict + ruff clean. NEXT: a new module slice, or harden/extend reflexes.

Prior milestone: **PULSE-exhaustion auto-locks the vault** (commit `b5d31af`) — the reflex TRIAD's operator
arm; `_apply_pulse_mode` issues `vault.lock` on the transition into `exhausted`. 3 RED->GREEN.

The reflex TRIAD — the "one mind" secures the vault from three angles:

- **Environment**: `tether.absent -> [vault.lock]` (dead-man — paired phone left range; commit `696e2e8`).
- **Threat**: `oracle.anomaly.detected -> [tether.heighten, vault.lock, chaff.generation.start, echo.start]` (fan-out + active obfuscation: CHAFF volume + ECHO timing; commits `ae3f405`, `837a739`, `5cfe243`).
- **Stand-down**: `tether.recovered -> [chaff.generation.stop, echo.stop]` (de-escalation — the reflex web's down direction; threat passed -> obfuscation organs relax; vault stays locked, no auto-unlock; commit `f51bdf0`).
- **Stand-down (matching axis)**: `oracle.anomaly.cleared -> [chaff.generation.stop, echo.stop]` (ORACLE all-clear; the score crossed back down through the hysteresis band; same axis that raised obfuscation now lowers it; commit `65bf8db`).
- **Operator**: PULSE `exhausted` -> `vault.lock` (cognitive reflex in the gate; commit `b5d31af`).
✅ **LIVE-WIRE-VERIFIED e2e** (core + real VAULT daemon + real hdiutil RAM mount): unlock -> publish
`tether.absent` -> relay issued `vault.lock` -> daemon locked + unmounted (vault_open False, /Volumes gone)
-> clean. The "one mind" runs on real hardware.
✅ **FULL-ORGANISM DEMO-VERIFIED e2e** (throwaway script, day 16): real core + real VAULT daemon + live
`watch` stream + `status` between acts. All THREE reflex arms fired live and locked the vault each time —
`tether.absent`, PULSE `exhausted` (status showed `PULSE: exhausted`), and `tether.escalation` L2
(`lock_vaults`) — with the `watch` stream narrating and `status` showing VAULT open->locked transitions;
clean teardown (KEK evicted, mounts gone). The complete organism demonstrably defends itself on real
hardware.

Prior milestone: **TETHER-loss auto-locks the open vault** (commit `696e2e8`) — first cross-module reflex;
`tether.absent -> vault.lock` on the relay path (the paired phone leaving range locks the open vault + tears
down its RAM mount). 1 RED->GREEN.

Prior milestone: **mount-to-tmpfs — decrypted plaintext lives only in a RAM-backed mount** (commits
`fe7af34` VD-9a + `d356074` VD-9b). The VAULT capstone. New mount seam (`mount.h`/`mount.c`): on a
state-gated ALLOW, `vault.unlock` opens a RAM-backed mount and materialises each decrypted file into it
(never to disk), returning the `mount` path; `vault.lock` / auto-relock / `vault.delete` /
`vault.policy.update` all `vault_mount_end` -> the plaintext **vanishes the moment the vault is locked by
any path**. The real backend attaches a macOS RAM disk (hdiutil + HFS+, manual-tier, live-verifiable); the
seam injects a temp-dir backend so no test mounts a real volume. 5 RED->GREEN Unity (74 VAULT). 960 -> 965.
🎯 **VAULT is functionally COMPLETE** — every method real, plaintext RAM-only, full lifecycle. The lone
manual-tier path is the real hdiutil backend (like shim ops). NEXT: live-verify the real mount, or move to
another module.

Prior milestone: **vault.policy.update — VAULT IPC fully real** (commit `3e47f25`) — VD-8, the last gated
method. Validates the new DSL (-32602), rewrites the policy, closes the vault if open; REFUSES a non-empty
vault (`vault_not_empty` — re-keying would orphan ciphertext). `is_engine_method` removed; every `vault.*`
method is real. 5 RED->GREEN Unity.

Prior milestone: **vault.delete — registry drop + KEK eviction + content wipe** (commit `60e13a6`) — VD-7.
`vault.delete {vault_id}` drops the vault from `registry.json`, evicts its KEK from the Keychain (new `del`
backend hook; real `SecItemDelete`, manual-tier), unlinks `<vault_id>.files.json`, closes it if open.
`{ok:true}`; unknown id -> `{ok:false, reason:no_such_vault}`. 2 RED->GREEN Unity.

Prior milestone: **decrypt-at-unlock — open sealed files with the gated key** (commit `3605bb6`) — VD-6.
On ALLOW `vault.unlock` OPENS the vault's sealed files (`vault_open_all`): re-derives the key,
`vault_crypto_open`s each `{nonce, ct}` (Poly1305 tag verified). All verify -> `{ok, files:N}`; a bad entry
-> `{denied:integrity}`. Closes the `add_file -> unlock` crypto round-trip end-to-end. 1 RED->GREEN Unity.

Prior milestone: **vault.add_file seals content into the open vault** (commit `daf43d2`) — VD-5. The vault
holds REAL encrypted content. `vault.add_file {vault_id, source_path}`: requires UNLOCKED, re-derives the
key, XChaCha20-Poly1305-seals the source file (capped 64 KiB), appends `{name, nonce, ct}` to
`<state_dir>/vault/<vault_id>.files.json`. Locked -> -31004. 2 RED->GREEN Unity.

Prior milestone: **vault.lock + auto-relock timer** (commit `f1c1e57`) — VD-4c. `vault.lock` clears the
open vault + relock timer; `vault.unlock` arms `relock_at = now + 900s` on ALLOW; `vault_runtime_tick`
auto-locks when due (daemon loop calls it each iteration). 2 RED->GREEN Unity. The open/close lifecycle
is complete.

Prior milestone: **unlock derives the state-gated key from the Keychain KEK** (commit `4060d7b`) — VD-4b.

Prior milestone: **unlock derives the state-gated key from the Keychain KEK** (commit `4060d7b`) — VD-4b.
On ALLOW `vault.unlock` DERIVES the vault key: keychain master secret + BLAKE2b(policy_dsl) + salt(vault_id
bytes) -> Argon2id. Key materialises ONLY on ALLOW; keychain/KDF failure -> `{denied:key_unavailable}`.
`sodium_memzero`'d immediately. DECRYPT + mount DEFERRED. 1 RED->GREEN Unity.

Prior milestone: **vault.unlock state-gated decision** (commit `b0856f5`) — VD-4a. `vault.unlock {vault_id}`:
looks up the policy in the registry, gathers a `VaultContext` (injectable provider seam), runs
`vault_policy_decide` -> ALLOW marks open + `{ok}`; DEFER -> `{defer}`; DENY -> `{denied:policy}`. Only ONE
vault open (`another_vault_open`); unknown id -> `no_such_vault`. 4 RED->GREEN Unity.

Prior milestone: **per-vault Keychain KEK; vault.create provisions it** (commit `2240961`) — VD-3. Gives
the shim's evict (PURGE Tier-0) REAL targets. `vault_keychain_load_or_create`: `SecItemCopyMatching`
{generic-password, service `com.umbra.chimera`, account=vault_id}; absent -> arc4random 32 bytes +
`SecItemAdd`. Swappable backend (setUp installs in-mem so no test touches the real Keychain; real SecItem
manual-tier). `vault.create` provisions the per-vault master secret. Makefile links Security +
CoreFoundation. 3 RED->GREEN Unity.

Prior milestone: **vault.create + vault.list with a persisted registry** (commit `e7c1b0c`) — VD-2.
`vault.create {name, policy_dsl}`: validates policy_dsl through the REAL parser (fail-closed -> -32602),
generates a 16-byte arc4random `vault_id`, persists `{vault_id, name, policy_dsl}` to
`<state_dir>/vault/registry.json`. `vault.list` reads it. `meta_dir` from `CHIMERA_STATE_DIR`. 3 RED->GREEN.

Prior milestone: **VAULT daemon skeleton — socket loop + vault.* dispatch** (commit `af35113`) — VD-1.
VAULT was a pure LIBRARY; now a live DAEMON: connects core.sock, registers `vault.*` + events, poll(500ms)
serve loop with heartbeats. `vault.status` real; engine methods gated -31004. Added vendored cJSON + shared
jsonrpc + the `vault` binary target. 4 RED->GREEN Unity.

Prior milestone: **Supervisor.purge_kill — emergency-choreography SIGKILL** (commit `64d569e`) — PURGE T0-c.
`Supervisor.purge_kill(grace=0.5)`: after a grace, SIGKILL every supervised proc still alive (ack-or-die,
§5.8 step 1); self-exited procs skipped. Wired in run_up via a `purge.imminent` subscription, so the chain
is `core.purge` -> publish `purge.imminent` -> supervisor SIGKILLs modules -> Tier-0. Per-module graceful
key-zeroing (C side) is follow-on. 2 RED->GREEN units (11 supervisor).

Prior milestone: **core.purge operator command — trigger -> real Tier-0** (commit `b913272`) — PURGE T0-b.
`core.purge` (operator surface command, like `core.lock`): broadcasts `purge.imminent` then runs
`run_tier0(shim, state_dir)` (evict CHIMERA Keychain via the shim + wipe state DBs). ARCHITECTURAL FINDING:
`purge.imminent` is emitted BY core, not PURGE — C modules have NO event-emit path (they only RECEIVE
events), so core is the orchestrator; PURGE's `purge.trigger` stays the module-side planner/preview.
3 RED->GREEN units.

Prior milestone: **core Tier-0 executor — first real consumer of the shim** (commit `155bd46`) — PURGE
T0-a. `core/tier0.py run_tier0(shim, state_dir)`: keys-first — `await shim.evict()` (CHIMERA Keychain
items) then wipe the on-disk state DBs (ORACLE baseline / PULSE history / VAULT metadata) under
`state_dir`. Best-effort: a shim failure never aborts the state wipe; returns `{keychain_evicted,
state_files_removed, errors}`. State files unlinked, NOT secure-overwritten (honest re SSD §8). shim param
a structural Protocol; blocking file I/O via `asyncio.to_thread`. 3 RED->GREEN units.

Prior milestone — **LIVE-VERIFIED Slice 3** (no commit; reinstalled the daemon): `sudo deploy/install-shim.sh`
put the new shim + core.req live; `dist/chimera/chimera shim-check` (signed core) vs the real
`/var/run/chimera-shim.sock` -> `handshake: ok — secret obtained`; `python -m core shim-check` ->
`-31007 not attested`. The whole channel→peercred→secret→SecCode-attestation chain proven against the
production root daemon (the old daemon gave -31002). The live daemon now carries real lock/evict/reboot.

Prior milestone: **reboot real + killall documented no-op — ALL 4 shim ops defined** (commit `e93d43a`)
— Slice 3c. `ops_execute(REBOOT)` runs an injectable reboot action; default = `/sbin/reboot`, secret-gated.
SH-11 honoured (setUp safe stand-in + recording reboot in tests). killall stays an EXPLICIT documented
no-op (GD redundancy; no safe self-identifying target). Privileged action layer COMPLETE: lock/evict/reboot
real, killall honest no-op. 1 RED->GREEN Unity (38/38).

Prior milestone: **evict op performs a real CHIMERA Keychain eviction** (commit `1e014a7`) — Slice 3b,
the first DESTRUCTIVE real op. `ops_execute(EVICT)` deletes CHIMERA generic-password items (service
`com.umbra.chimera`: VAULT master secrets, TETHER IRK) from the CONSOLE operator's login keychain via
`launchctl asuser /usr/bin/security delete-generic-password`, looped until none remain (idempotent; root's
keychain is NOT the target). Secret-gated. MANUAL-TIER; modules don't store these items yet (deletes 0).

Prior milestone: **lock op performs a real screen lock** (commit `057b5a8`) — Slice 3a. `ops_execute(LOCK)`
runs an injectable lock action (`did_noop=0`); the default sleeps the display via `/usr/bin/pmset
displaysleepnow` (with require-password-after-sleep this locks — the reversible operator command,
SS-2/§8.8). Test safety: `setUp` swaps in a harmless lock action; the ops test injects a recording
stand-in. Real pmset effect is MANUAL-TIER (to try live: reinstall the shim + trigger `core.lock`).

Prior milestone: **live 2b attestation PROVEN + shim-check diagnostic** (commit `6698faa`). Added
`chimera shim-check` (ping + handshake; prints the outcome, never the secret; `CHIMERA_SHIM_SOCKET`
override; standalone — dispatched before `_config_from_env`, needs no core config). PROVED the whole
Slice 2 secret-auth chain end-to-end LOCALLY (no sudo): a signed shim on a temp socket pointed at core's
captured DR — the SIGNED core (`dist/chimera/chimera shim-check`) gets `handshake: ok — secret obtained
(64 hex)`; the UNSIGNED `python -m core shim-check` gets `-31007 not attested`. Same code, two binaries,
opposite verdicts -> SecCode audit-token attestation genuinely distinguishes core from a same-uid process.

Prior milestone: **SecCode peer attestation gates secret issuance** (commit `529751e`) — Slice 2b-ii.
`attest.c`: `attest_peer_is_core(fd, requirement)` = `LOCAL_PEERTOKEN` ->
`SecCodeCopyGuestWithAttributes(kSecGuestAttributeAudit)` -> `SecCodeCheckValidity` vs a `SecRequirement`;
fail-closed on any NULL/error/non-match. main reads core's DR from `--core-req PATH` and feeds
`attest_peer_is_core(conn, req)` as shim.handshake's `attested` verdict. `install-shim.sh` captures
core's DR (`codesign -d -r-`) to `/usr/local/libexec/chimera/core.req`; absent -> NULL -> no secret.
Makefile links Security + CoreFoundation. 3 RED->GREEN Unity fail-closed seams (36/36).
NOTE: the LIVE root daemon at `/var/run/chimera-shim.sock` is still the OLD pre-2b binary (handshake ->
-31002); reinstall via `sudo deploy/install-shim.sh` when you want the running daemon updated (the local
proof above used a temp-socket shim, so it needed no reinstall).

Prior milestone: **ShimClient handshake + secret on destructive ops** (commit `a40a0c5`) — Slice 2b-iii.
`ShimClient.handshake()` calls `shim.handshake` -> caches the issued per-boot secret; `_ensure_secret()`
handshakes once, lazily; `evict/reboot/killall` now send `{"secret": <cached>}` (ping/lock unchanged).
3 RED->GREEN integration (handshake returns secret; evict handshakes then carries it; secret cached ->
one handshake). 918 -> 921. NEXT: shim Slice 2b-ii — `attest.c` (LOCAL_PEERTOKEN -> SecCode vs core's
DR from a root-only install config) wires the real `attested` verdict (manual-tier); then Slice 3 ops.

Prior milestone: **shim.handshake issues secret to an attested peer** (commit `ad1bc6a`) — Slice 2b-i.
`protocol_dispatch` gained an `attested` verdict (the audit-token SecCode result, injected like
`authorized`). New `shim.handshake`: peercred-authorized AND attested -> `{"secret": <per-boot>}`;
else -31007. main passes `attested=0` for now (FAIL-CLOSED) so the live shim issues no secret and
destructive ops stay sealed until 2b-ii wires real SecCode attestation. 3 RED->GREEN Unity (33/33).
915 -> 918. NEXT: shim Slice 2b-ii — `attest.c` (LOCAL_PEERTOKEN -> SecCodeCreateWithAuditToken ->
SecCodeCheckValidity vs core's DR captured at install); then 2b-iii core ShimClient.handshake.

Prior milestone: **core signed as a standalone binary** (commits `399509f`/`7630fb3`/`94049a8`) —
slice A, the §5.5 prerequisite for shim Slice 2b. core is frozen to a onedir Mach-O
(`deploy/build-core.sh`, PyInstaller) and deep-signed with hardened runtime under one identity
(`deploy/sign-core.sh`): 132 nested Mach-O + the exe, verified `flags=runtime`, NO get-task-allow,
NO disable-library-validation, still runs. Core's designated requirement is stable across rebuilds
(identifier "chimera" + Apple Development leaf, NOT cdhash) — the pin the shim verifies in 2b.
`launch_agent_plist` now targets the frozen binary (`chimera up`, not `-m core up`) under `sys.frozen`.
WHY A existed: 2b's secret handoff needs the shim to tell core from a same-uid process, but
`python -m core` peers resolve (via SecCode) to the python interpreter — indistinguishable — so core
had to become its own signed binary first. +2 cli unit. 913 -> 915. NEXT: shim Slice 2b — audit-token
peer attestation (build SecRequirement from core's DR captured at install) + secret issuance to the
verified core; then Slice 3 real op effects.

Prior milestone: **shim per-boot secret gates destructive ops** (commit `2b92ef9`) — Slice 2a, SS-2/3.
`secret.{h,c}`: per-boot secret = 32 arc4random bytes hex-encoded (in-memory only, SS-4) + constant-
time `secret_equal`. `protocol_dispatch` now REQUIRES `params.secret` == the per-boot secret for the
destructive ops (evict/reboot/killall) -> -31007 otherwise; lock/ping stay peercred-only (SS-2 staged,
lock reversible). main generates the secret at load + threads it through serve_one. Enforces "no
destructive op authed by peercred alone" at the protocol. 7 RED->GREEN Unity (30/30 shim). 906 -> 913.
⚠️ DEFERRED: Slice 2b — the secret HANDOFF to core (shim verifies the peer's CODE SIGNATURE via audit
token + SecCode, then issues the secret only to the verified signed core); Slice 3 real op effects.

Prior milestone: **graceful-then-force shutdown** (commit `14671c3`) — GD, §7.7. `Supervisor.down`
now SIGTERMs every module (reverse launch order), waits up to `shutdown_grace`, then SIGKILLs any
straggler still running (`SupervisedProc` gained kill()/poll()). HONEST §8.8(d) note: the spec lists
`shim.killall` (core->shim) for shutdown, but the supervisor OWNS its module procs (Popen handles) so
it SIGKILLs them directly — `shim.killall` is redundant for supervisor-owned processes (it would only
be needed for procs the unprivileged side can't kill). 1 RED->GREEN unit; ruff + mypy clean. 905 ->
906. NEXT: evict/reboot await PURGE's real (gated) trigger; shim Slice 2 per-boot secret; Slice 3 ops.

Prior milestone: **core.lock -> privileged shim** (commit `83dd0ca`) — P4c. The privileged chain is
now CLOSED end to end: `core.lock` (operator command, §8.8) -> `_handle_lock` -> `ShimClient.lock()`
-> the live root shim -> `{ok,noop}`. Server gained `shim_client` (build_core wires it); no shim ->
-31004; ShimError -> -31004. Verified against the LIVE signed root shim (lock is a Slice-1 no-op, so
no screen lock). 3 RED->GREEN (1 unit + 2 integration incl live); ruff + mypy clean. 902 -> 905.
NEXT: the other ops (evict/reboot/killall) + their real triggers (TETHER L1 / PURGE / shutdown);
shim Slice 2 per-boot secret; shim Slice 3 real op effects (destructive ones last, §5.4).

Prior milestone: **core ShimClient + privileged shim LIVE** (commit `46db506`) — P4b + platform
P1/P2/P4a. The privileged root channel is REAL and live-verified end to end: the shim is signed
(operator's Apple Development cert via `deploy/sign.sh`), installed as a root LaunchDaemon
(`deploy/install-shim.sh` -> /Library/LaunchDaemons), its socket reachable (`ownership_apply` GREEN
-> 0660 root:staff, SS-0), and `core/shim_client.py` (`ShimClient.call` + ping/lock/evict/reboot/
killall) talks to it over JSON-RPC — verified against a fake shim AND the LIVE shim (ping -> pong,
peercred-authorized). 5 RED->GREEN integration; ruff + mypy clean. 897 -> 902. NOTE: code-signing
keystone done the local way — sign.sh auto-uses a VALID keychain identity (self-signed needs GUI
trust; Keychain Access is hidden behind the Passwords app on this macOS — created via Certificate
Assistant if no Apple cert). NEXT: P4c — wire a real op into core logic (e.g. gate/TETHER -> shim.lock) + shim Slice 2 per-boot secret (the destructive ops stay no-op until then).

Prior milestone: **crash-restart** (commit `6f43c72`) — CR-1. Closed the self-heal gap: an abruptly
killed module (socket drops, no graceful core.deregister) used to stay REGISTERED forever (the sweep
only FAILs HEALTHY/DEGRADED on missed heartbeats). `Registry.mark_lost(name)` now turns a live module
-> FAILED on abrupt loss; `server._serve_commands` calls it in the finally (a graceful deregister ->
STOPPED is a no-op). Composes with the SV-5'b autonomy link: crash -> FAILED -> supervisor re-spawn.
So BOTH a hung module (sweep) and a killed process (disconnect) now self-heal. 4 RED->GREEN (3 unit +
1 integration: kill echo -> core marks it FAILED); ruff + mypy clean. 893 -> 897.

Prior milestone: **supervisor autonomy link + consolidation** (commits `789a5cb` refactor + `43f580d`)
— SV-5'. Closed a real DUPLICATION: supervisor.py had its own RestartTracker + backoff_delay +
restart that byte-identically duplicated core.lifecycle's §7.5 (a SV-3 miss — didn't check lifecycle
first); removed them, lifecycle is the single source of truth. Then wired the autonomy LINK that was
genuinely missing: `Supervisor.handle_failure` (delegates the restart decision to lifecycle, re-spawns
only on -> STARTING) + `on_state_changed` (broker hook, acts on FAILED only); `run_up` subscribes to
module.state_changed and drains it — so a hung module core marks FAILED is auto-re-spawned within
budget. Net 4 RED->GREEN unit (−7 removed dup + 4 new); ruff + mypy clean. 896 -> 893. NOTE: this
fires on the FAILED (missed-heartbeat) path; a cleanly-crashed process disconnects -> STOPPED, which
is a separate core concern (deferred). Discovery: core lifecycle already owned §7.4 sweep + §7.5.

Prior milestone: **chimera up CLI** (commit `ae64244`) — SV-4, CLOSES the day-14 supervisor arc.
`core/__main__.py`: `parse_args` (subcommands `up` = whole organism, `plist`; none = bare core) +
`module_binary` resolver + `_default_spawn` (launches module daemons) + `run_up` (build_core +
start + Supervisor waves + serve-until-signal + graceful down) + `launch_agent_plist` (§7.10). Verified:
`python -m core up` brings ECHO+PURGE alive against core (both status round-trip) and exits cleanly
on SIGTERM. 6 RED->GREEN (5 unit + 1 integration); ruff + mypy --strict clean. 890 -> 896. The
arc is whole: SV-1 core entry, SV-2 dependency waves, SV-3 restart/backoff, SV-4 `chimera up`.
NEXT (deferred): live heartbeat monitor wiring restart() on crash; privileged shim (§8.8, platform).

Prior milestone: **restart policy** (commit `9481c1f`) — SV-3, day-14 supervisor arc (§7.5).
`supervisor.py`: `backoff_delay` (1/2/4/8s then 30s cap) + `RestartTracker` (rolling-window budget,
prunes old) + `Supervisor.restart(name, now)` — respawns within budget, returns the backoff delay,
and after MAX_RESTARTS (5/hour) gives up -> PERMANENTLY_FAILED (`dead`). Pure + DI (injected now /
fake spawn), fully unit-tested. 7 RED->GREEN; ruff + mypy --strict clean. 883 -> 890. NEXT: SV-4
chimera up/down CLI + LaunchAgent plist (the visible payoff: one command brings the organism alive) + wiring restart into a live heartbeat monitor.

Prior milestone: **module supervisor** (commit `e8102c9`) — SV-2, day-14 supervisor arc. `core/
supervisor.py`: `topological_waves(specs)` layers modules into dependency waves (§7.3; rejects
cycles + unknown deps — pure, unit-tested) + `Supervisor` (DI spawn/is_registered) that launches
each wave and waits for registration within `wave_timeout` (fail-closed, not fail-stuck), tears
down in reverse. Verified bringing the real ECHO+PURGE daemons up via the supervisor against a live
core. 9 RED->GREEN (8 unit + 1 integration); ruff + mypy --strict clean. 875 -> 883. NEXT: SV-3
restart/backoff (§7.5), SV-4 chimera up/down CLI + LaunchAgent plist.

Prior milestone: **core entry point** (commit `40974ff`) — SV-1, first slice of the day-14 supervisor
arc ("the organism runs"). Brought `core/__main__.py` to life: `build_core(config)` wires
broker+lifecycle+registry+tokens+OverrideStore+Server; `serve_forever()` starts then runs until
SIGTERM/SIGINT and stops gracefully; `main()` reads CHIMERA_SOCKET_DIR. `python -m core` now runs a
real core that serves core.* and exits cleanly on SIGTERM. 5 RED->GREEN (3 unit + 2 integration);
ruff + mypy --strict clean. 870 -> 875. NEXT in the arc: SV-2 supervisor (start core -> wait socket
-> launch module daemons in dependency waves §7.3), SV-3 restart policy, SV-4 chimera up/down CLI + LaunchAgent plist.

Prior milestone: **ARCHITECTURE §8 I3 reconciliation** (commit `c770309`) — B2a, a docs/spec fix (no
test change; 870). Closed a real spec-vs-code contradiction: §8 I3 read absolute "fail-closed, never
fail-open", but the built cognitive gate (PULSE + `core/gate.py`) fails OPEN by design. I3 now
scoped — secrecy/safety state fails CLOSED (vault relock, traffic pause); the operator-autonomy
layer fails OPEN (broken fatigue sensor must never lock the operator out, §5.5). Same class as the
PULSE.md 7->14d catch (BS-1). Also refreshed the stale "Part 1 of 5" title (the doc is whole). NOTE:
the root CLAUDE.md still carries 2 stale "Part 1" lines (outside chimera/ — left untouched pending
the operator's ok).

Prior milestone: **multi-module e2e (consolidation)** (commit `8e963d8`) — CO-1…3. First proof the
organism breathes with MANY live modules at once: one core.Server + the ECHO and PURGE C daemons
(subprocesses) + a PULSE Python client (in-process) all register CONCURRENTLY, core.capabilities
sees all three, and each answers its own status with no cross-talk. A confirmation test (passed on
write — the core/registry/4A router holds N concurrent modules correctly). 869 -> 870.

Prior milestone: **PURGE socket loop — live daemon** (commit `3acf1f7`) — §6, PL-1…6. PURGE is now a
LIVE registered module (mirrors ECHO): `ipc.{h,c}` + `daemon.{h,c}` (poll/dispatch/heartbeat) +
`main.c` (connect core.sock, core.register {purge, 10 methods, 4 events}, run). `make` builds the
binary (STRICT); 2 integration RED->GREEN (registers + answers purge.status; 10.5s -> 0.61s). Both
ECHO + PURGE are now live daemons. 867 -> 869. ⚠️ purge.trigger stays -31004; the real destruction
engine (Keychain/Mach VM/dc zva/libsodium) remains gated.

Prior milestone: **PURGE command dispatch** (commit `76b7b10`) — §7 IPC, PD-1…5. PURGE's daemon heart
(links cJSON + common/jsonrpc): `commands.{h,c}` — `purge_runtime_t {targets, config, armed}` +
`purge_commands_dispatch(method, params, id) -> JSON`: purge.status / config.get|set / target.add|
remove|list (over the registry) / test (the dry-run plan — DESTROYS NOTHING) / arm (phrase required)
| disarm. **purge.trigger is GATED -> -31004** (the destruction engine is not built; no faked wipe,
§4/§6). unknown -> -32601. 12 Unity RED->GREEN (35/35 PURGE total). ⚠️ DEFERRED: socket loop
(ipc/daemon/main) + the real destruction engine (Keychain/Mach VM/dc zva/libsodium).

Prior milestone: **ECHO socket loop — live daemon** (commit `b223236`) — §6, EL-1…6. ECHO is now a
LIVE registered module: `ipc.{h,c}` (UNIX-socket client + NDJSON reader, mirrors CHAFF) +
`daemon.{h,c}` (single-threaded poll loop: dispatch routed echo.* -> respond, heartbeat, exit on
EOF/SIGTERM) + `main.c` (connect core.sock from CHIMERA_SOCKET_DIR, core.register {echo, 6 methods,
3 events}, run). `make` builds the binary (STRICT); 2 integration RED->GREEN (the echo binary
registers + answers echo.status against a live core.Server; 10.5s timeouts -> 0.56s). 853 -> 855.
⚠️ DEFERRED: real pf/BPF packet shaping (root/kernel — gated).

Prior milestone: **ECHO command dispatch** (commit `c89844d`) — §5 IPC, ED-1…5. The first daemon
slice — ECHO now links cJSON + the shared `common/jsonrpc` (build-system update). `commands.{h,c}`:
`echo_runtime_t {config, stats, running}` + `echo_commands_dispatch(method, params, id) -> JSON`,
the hermetic heart of the daemon — echo.status / config.get / config.set (validated via the config
core, -32602 on bad) / stats (ratio + decile histogram) / start|stop (running flag) / unknown ->
-32601. 8 Unity RED->GREEN (31/31 ECHO total). ⚠️ DEFERRED: the socket loop (connect core.sock +
register + serve + heartbeat — ipc.c/main.c) + real pf/BPF shaping.

Prior milestone: **gate hardening — override change-requires-current** (commit `db19bd5`) — GH-1…4,
§8. Closes the last gate/override gap: `OverrideStore.set_phrase(phrase, *, current=None)` now
REJECTS a change to an existing phrase unless the correct current phrase is given (returns False,
old phrase stays active); the first set still needs none. `core.override.set` passes the optional
{current} and maps a rejected change to -31007 NOT_AUTHORIZED — so surface access alone can no
longer silently reset the gate escape. 6 RED->GREEN (4 store + 2 handler); ruff + mypy --strict
clean. 839 -> 845. **The hermetic Python core is now fully built.**

Prior milestone: **PURGE config core** (commit `811a261`) — §7/§4/§8, PC-1…5. PURGE's post-purge
settings: `config.{h,c}` — `purge_config_t {post_action, marker}` + `purge_config_default()` =
{PURGE_REBOOT (§4), marker off (§8 deniability)} + `purge_post_action_from_str`/`_str`
(reboot/shutdown/stay round-trip, -1 on unknown) + `purge_config_set(cfg, *post_action, *marker)`
— atomic partial update (invalid action -> -1, cfg untouched). 7 Unity RED->GREEN (23/23 PURGE
total). ⚠️ DEFERRED: IPC purge.config.set/get (daemon) + persistence.

Prior milestone: **PURGE target registry** (commit `aea7b86`) — §3/§7, PR-1…5. The operator's
Tier-2 destruction list: `targets.{h,c}` — a bounded (64) in-memory `purge_targets_t` of
{path, encrypted} with `purge_target_add` (idempotent by path; rejects NULL/empty/too-long/full
with -1), `purge_target_remove` (idempotent), count/at accessors, and `purge_plan_targets()`
bridging the registry into the dry-run plan (encrypted -> shred, unencrypted -> skip). 9 Unity
RED->GREEN (16/16 PURGE total). ⚠️ DEFERRED: persistence (~/.config/chimera/purge/) + IPC
purge.target.* (daemon) + gated encryption detection (encrypted flag operator-supplied for now).

Prior milestone: **PURGE dry-run planner** (commit `1481d6d`) — §5.8 §4/§8, PG-1…5. The 8TH and
FINAL organ starts — **all 8 modules now underway**. A NEW C module (`modules/purge/`, mirrors
CHAFF/ECHO). First slice = the `purge.test` dry-run + the §8 honest-wipe rule, and it DESTROYS
NOTHING: `purge_classify(encrypted)` → SHRED if encrypted, else SKIP_UNENCRYPTED (PURGE refuses
to pretend-wipe unencrypted SSD — no security theatre); `purge_build_plan(...)` builds the
keys-first tier report (Tier 0 + Tier 3 always-on, Tier 1 configurable, Tier 2 classified only
when enabled). 7 Unity RED->GREEN; added to check.sh. ⚠️ DEFERRED/GATED: ALL real destruction —
Keychain eviction, Mach VM, ARM64 dc zva, libsodium/explicit_bzero, the daemon + purge.arm/trigger + emergency choreography.

Prior milestone: **ECHO stats core** (commit `a0a8014`) — §5.2 §5, ET-1…5. ECHO's accounting:
`stats.{h,c}` — `echo_stats_t` accumulates per-tick (real, padding) into totals + a 10-bin decile
histogram of per-tick padding ratio (idle ticks land in the top bin, active in the bottom —
disambiguates §5's vague "histogram"). `echo_padding_ratio_pct` = overall padding share (0 if
empty, no div-by-zero); `echo_padding_surge(threshold)` = the §5 echo.padding.surge trigger
(ratio >= 80%). 7 Unity RED->GREEN (23/23 ECHO total). With this ECHO's pure LOGIC is complete
(shaper + config + stats). ⚠️ DEFERRED: windowed 1m/1h/1d query (needs a timestamped ring
buffer) + IPC echo.stats + echo.padding.surge emission (all daemon).

Prior milestone: **ECHO config core** (commit `2f381ce`) — §5.2 §3, EC-1…5. The operator knobs
for ECHO: `config.{h,c}` — `echo_config_t {target_kbps, burst_tolerance}` + `echo_config_default()`
= {100, 200} (§3) + `echo_config_valid()` (range bounds) + `echo_config_set(cfg, *target, *burst)`
— a partial update (NULL = unchanged) that validates ALL provided fields and rejects ATOMICALLY
(cfg untouched on a bad value) + `echo_config_budget(cfg, tick_ms)` bridging config -> the shaper.
7 Unity RED->GREEN (16/16 ECHO total). ⚠️ DEFERRED: IPC echo.config.set/get (needs the ECHO
daemon, not built) + persistence to ~/.config/chimera/echo/.

Prior milestone: **ECHO shaper core** (commit `ca06b25`) — §5.2 §3, ES-1…6. A NEW C module
(`modules/echo/`, mirrors CHAFF's scaffold — strict-c17 Makefile + Unity), the bandwidth-
normalizer pair to CHAFF. First hermetic slice = the pure constant-rate-padding math:
`echo_budget_bytes(target_kbps, tick_ms)` (100KB/s @10ms = 1024 B/tick) + `echo_shape(queued,
budget, burst) -> {real_send, padding}` = min(queued, budget+burst) real + max(0, budget-real)
padding, so the WIRE stays FLAT at budget whenever queued <= budget (the hiding guarantee —
idle and light traffic look identical on the wire), bursting to budget+burst to drain a backlog.
9 Unity RED->GREEN; added to check.sh. ⚠️ DEFERRED/GATED: pf/BPF packet I/O + raw sockets +
padding emission (root/kernel, like MIRROR's tap) + config/stats DB + IPC/jsonrpc daemon (echo.*).

Prior milestone: **PULSE §6 finishers — calibrate + pulse.error** (commit `53547ad`) — PF-1…7,
closing PULSE's §6 method surface. Store (`baseline.py`): `calibration_days(now)` = distinct days
in the window (baseline_ready now reuses it, DRY) + `clear()` wipes all buckets. Daemon
(`client.py`): `pulse.calibrate.start` reports {days_observed, days_required:14, ready, started_at}
and stamps the calibration epoch (idempotent); `pulse.calibrate.reset` clears the store to
recalibrate (operator-invoked). `_safe_tick` wraps the tick loop — on ANY error it emits
`pulse.error {where, message}` and continues (fail-open §8), making the registered-but-silent
pulse.error event a real producer. 5 unit RED->GREEN; ruff + mypy --strict clean. 788 -> 793 (+5).
PULSE's §6 surface is now COMPLETE; only its live signal inputs remain gated.

Prior milestone: **core.override.set** (commit `22aebc7`) — operator set-phrase path, OS-1…4.
A new core method lets the OPERATOR set/change the gate-override phrase: `_handle_override_set`
is surface-only (a module connection — even with a valid core token — is refused -31007; the
phrase is the operator's, never a module's), needs a configured OverrideStore (-31004) and a
non-empty phrase (-32602), then calls set_phrase. 5 unit RED->GREEN (via handle_command with a
surface/module Connection); ruff + mypy --strict clean. 783 -> 788 (+5). The whole gate+override
chain is now operator-controllable end to end. ⚠️ DEFERRED: change-requires-old-phrase hardening,
confirm-dialog (surface), external-OS gating.

Prior milestone: **override-phrase store** (commit `3564968`) — §8 autonomy escape, OV-1…6.
`core/override.py` `OverrideStore`: a salted PBKDF2-SHA256 hash of the operator's override
phrase (random 16-byte salt, 200k iterations) persisted as JSON at override.json (0600) — the
phrase is NEVER stored in the clear; verify() is constant-time (`hmac.compare_digest`) and False
when unset. Wired into the gate (OV-3): `_gate(method, params)` reads an `_override` phrase from
the request, verifies it, and passes override_ok to decide() — so an exhausted block is escapable
with the right phrase (§8: a speed bump, not a cage). `_route` STRIPS `_override` before
forwarding — the secret never reaches the module. 7 store-unit + 3 gate-wiring (override allows /
wrong blocks / strip) RED->GREEN; ruff + mypy --strict clean. 773 -> 783 (+10). ⚠️ DEFERRED: the
operator path to SET the phrase (a `core.override.set` method / CLI — set programmatically for
now) + confirm-dialog (surface) + external-OS gating.

Prior milestone: **core gate live-wiring** (commit `fbe64cc`) — GW-1…6, the gate now ACTS.
`core/server.py` enforces the §4 decision on the live command path: `_route` calls
`_gate(method)` before forwarding — a danger CHIMERA-command is BLOCKED at exhausted
(`-31003 DENIED_BY_POLICY`) or DELAYED at tired (asyncio.sleep), else forwarded. Core tracks
PULSE's mode (subscribes to `pulse.mode.changed`, GW-2) and refreshes the cached danger set
from `pulse.danger.list` when PULSE registers (GW-3, core-authority query). fail-OPEN
throughout: an unknown mode / refresh failure never blocks. 5 unit + 2 integration RED->GREEN
(integration 10.5s timeouts -> 0.24s — the wiring signal); ruff + mypy --strict clean. 766 ->
773 (+7). ⚠️ DEFERRED: confirm-dialog + override-phrase entry (need the surface — core can't
prompt mid-route), salted-hash override storage, gating of external OS actions (rm/git never
flow through core — need a CLI/shell gate), live danger-set refresh on registry change (only on
PULSE register now). override_ok is always False this slice.

Prior milestone: **core cognitive gate (decision)** (commit `7d6c8fa`) — §4 friction + §8
autonomy invariant, GE-1…5. `core/gate.py` `decide(action, mode, danger, *, override_ok)` ->
GateDecision: a danger action gets friction by PULSE's mode — normal→allow, caution→confirm,
tired→delay(5s), exhausted→block (a correct override escapes). Non-danger actions always allow.
fail-OPEN (§8): an unknown/None mode NEVER blocks — a broken cognitive sensor must not lock the
operator out (opposite of VAULT's fail-closed). The override phrase is a speed bump, never a
cage. Pure (no I/O), 8 unit RED->GREEN; ruff + mypy --strict clean. 758 -> 766 (+8). This is the
CONSUMER PULSE was missing — but only the DECISION heart; ⚠️ the live wiring (core tracks
pulse.mode.changed + caches the danger registry + hook in `_route` + real confirm/delay/block +
salted-hash override storage) is the next slice.

Prior milestone: **PULSE danger-registry** (commit `b87be5a`) — §5.5 §4/§6/§7, DR-1…6. The
operator-editable registry of danger-action signatures: `registry.py` `DangerRegistry` = plain
JSON at registry.json (NOT encrypted — operator config, not raw data; dir 0700 / file 0600),
seeds the §4 defaults on first use, add/remove idempotent. Wired into the daemon:
`pulse.danger.add/remove/list` via the 4A router (DangerRegistry injected; -31004 if absent),
each returns {registry:[...]}. 5 unit + 2 integration RED->GREEN; ruff + mypy --strict clean
(mypy caught a `list`-method-shadows-builtin + an Any-return — both fixed). 751 -> 758 (+7).
⚠️ DEFERRED: the CONSUMER — core gate-enforcement that reads the registry to gate actions — is
not built; the registry is the operator's editable list, no live gating yet.

Prior milestone: **PULSE mode.changed emission** (commit `76e9955`) — §5.5, EM-1…6. The daemon
now EMITS `pulse.mode.changed` on a mode transition: a tick-loop computes `_compute(now)`
(temporal_signal -> assess; primary_signal='temporal' — the only present group this slice), and
on a real mode change emits {old_mode, new_mode, score, primary_signal} as an advisory
Notification (announce ≠ act; core relays per §5). The first tick establishes `_last_mode` (no
emit). 3 hermetic client-unit RED->GREEN (FakeWriter + seeded store + injected now); ruff + mypy
--strict clean. 748 -> 751 (+3). ⚠️ emission is DORMANT during calibration (baseline_ready False
-> mode always 'normal' -> no transitions); it fires once calibrated / with live signals.
pulse.error not yet emitted.

Prior milestone: **PULSE daemon** (commit `44280d2`) — §5.5, PULSE becomes a LIVE module.
`client.py` (module-only, mirrors ORACLE's command connection): opens core.sock, core.register
(`pulse.*` + 2 events, depends_on=[]), serves `pulse.*` via the 4A router, heartbeats. `pulse.status`
composes the live edge — temporal_signal(now) feeds the empty `temporal` slot of assess(store,…)
-> {score, mode, baseline_ready, session_minutes}; advisory + fail-OPEN (uncalibrated -> mode
'normal', §8). pulse.weights.set (sum=1.0 validated) / enable / disable. `__main__.py` = `python -m
pulse` (CoreConfig + BaselineStore + signal-cancelled asyncio.run). 4 integration RED->GREEN
(wall-clock 20.75s timeouts -> 0.45s registered — the wiring signal); ruff + mypy --strict clean.
744 -> 748 (+4 integration). ⚠️ DEFERRED: events emission (mode.changed producer), calibrate/
danger/override subsystems, live signal collection (MIRROR group-A consumer, kqueue idle, ORACLE
drift), core gate-enforcement.

Prior milestone: **PULSE temporal — group B** (commit `abd2bf3`) — §5.5, the time-context
fatigue signal that fills the empty `temporal` slot in `assess`. `temporal.py` (pure,
hermetic) maps injected ISO times to one value in [0,1]: a chronotype-weighted hour-of-day
curve (peak ~3am, low midday; night_owl x0.4 on night hours) weighted 0.5 + hours-since-idle/6
clamped 0.25 + session-hours/12 clamped 0.25, all clamped [0,1]. now/session_start/last_idle_end
injected (no clock inside); a missing input contributes 0 (fail-OPEN §8, never inflates).
Chronotype is an input (auto-detect §9 deferred). 10 tests RED->GREEN; ruff + mypy --strict
clean. 734 -> 744 (+10). ⚠️ group-B SCORING done (hermetic); the LIVE collector (kqueue
idle-detection + real clock/session) is still gated.

Prior milestone: **PULSE slice 3 — assess wiring** (commit `54b2751`) — §5.5, the bridge
that connects PULSE's two halves. `assess.py` pulls each present group-A signal's 14-day
baseline from the store, normalizes the current reading via `normalize_delta` (fatigue
direction per GROUP_A_DIRECTIONS), means the present sub-deltas into ONE `input_delta`
(WS-3), builds `Signals`, and calls `score_and_mode` with
`baseline_ready=store.baseline_ready(now)` -> `(score, mode)`. Group-A contract (WS-2, the
PULSE side of gap D8, per §3): typing_speed (slower=fatigue), error_rate + mouse_ineff
(higher=fatigue); the VALUES are caller-supplied so assess stays decoupled from MIRROR's
wire format. temporal (B) + drift (C) caller-supplied this slice (their producers —
kqueue, ORACLE — deferred). Fail-safe inherited from score_and_mode (broken/all-absent ->
`normal`). 10 tests RED->GREEN; ruff + mypy --strict clean. 724 -> 734 (+10).

Prior milestone: **PULSE slice 2 — baseline store** (commit `bef89a6`) — §5.5, the
encrypted history store that feeds the scoring engine its two missing inputs. Mirrors
ORACLE's baseline.py: SQLite + cryptography.Fernet (key 0600 beside DB, dir 0700, db
0600, check_same_thread=False + RLock). Schema (BS-4): `buckets(id, ts plaintext, gated
plaintext, signals_json BLOB Fernet)` + idx + baseline_meta — ts/gated plaintext so SQL
windows + excludes BEFORE decrypt; aggregate signal VALUES Fernet-encrypted at rest (§5;
§8 — aggregates, never raw input). `baseline(key, now)` = 14-day rolling MEDIAN over
NON-gated buckets in half-open `[now-14d, now)`, None if none (BS-5);
`baseline_ready(now)` = >=14 distinct days in window (the 14-day cold-start gate, BS-8);
`purge(now)` drops buckets older than now-14d (BS-7). `signals` is an open {name:float}
dict (BS-9) — no MIRROR field names hardcoded (MIRROR->PULSE aggregate event undefined,
gap D8); `now` always injected as an ISO string (hermetic, deterministic). ⚠️ spec
amended FIRST (`2da2132`, BS-1): PULSE.md retention 7->14d — a 7-day store cannot feed a
14-day median (retention must be >= the median window). 24 tests RED->GREEN; ruff + mypy
--strict clean. ⚠️ STARTED, NOT complete — the store is hermetic; live producers (MIRROR
group-A, ORACLE drift, kqueue idle), the daemon/IPC, and core gate-enforcement remain
DEFERRED. 700 -> 724 (+24).

Prior milestone: **PULSE slice 1 — scoring engine** (commit `d9b0a42`) — §5.5
Cognitive Load Monitor, CHIMERA's first cognitive-state defense and the only module
that watches the OPERATOR, not the system/world. First hermetic slice: a pure-Python
scoring engine (mirrors ORACLE's form). Takes already-normalized signals + a baseline
snapshot -> `(fatigue_score, mode)`: weighted sum of present groups, weights
renormalized to sum 1.0 (§7), score clamped [0,1], mode by §4 thresholds half-open
`[lo,hi)`. ⚠️ **fail-safe = mode `normal`** — a missing/NaN/inf signal or all-absent
tick degrades to LESS friction, NEVER block (autonomy invariant §8, the OPPOSITE of
VAULT's fail-closed). Advisory: emits `(score, mode)`; core enforces gates. 22 tests
RED->GREEN; ruff + mypy --strict clean. ⚠️ slice 1 ONLY (the scoring math) — everything
else DEFERRED (see PULSE structure + open tails). 678 -> 700 (+22).

Prior milestone: **jsonrpc extract to `modules/common/` — JE-1 done** (4 native
modules migrated to one canonical shared unit: chaff `24cf41f` pilot, mirror
`611c16c`, shim `c25dfec`, tether `2245f09`). The four byte-identical (modulo
namespace) per-module jsonrpc copies collapse into `modules/common/{jsonrpc.h,
jsonrpc.c}` with a canonical `jsonrpc_result_t {OK=0, ERR=-1, ERR_PARSE=-2}` and an
`extern "C"` guard (front-loaded in the pilot for the C++ tether link). Each
migration proven behaviour-preserving: a formal normalized-diff = only the one-line
top comment, 0 difference in function bodies, + the module's suite green. C++ tether
verified at link too (common compiled as C via `clang -std=c17`, linked by clang++,
0 undefined symbols — extern "C" holds). TE-7b debt paid, before a 5th copy (VAULT).
678 baseline UNCHANGED (move+rename, 0 new tests). Each native suite re-verified:
chaff 46, mirror 42, shim 23, tether 48, vault 44.

Prior milestone: **VAULT crypto engine** (commit `e82f69b`) — the FIFTH native
module gets real cryptography via libsodium (the first VAULT external dependency;
the pure-C phase ends here, deliberately). Three primitives:

- `vault_crypto_derive` — Argon2id MODERATE (crypto_pwhash, OPSLIMIT/MEMLIMIT_MODERATE,
  ALG_ARGON2ID13); password = master_secret ‖ policy_hash (binds the key to the
  policy). The combined buffer holds the RAW master secret → it lives in sodium_malloc
  secure memory and is sodium_free'd (zeroed) the instant derivation ends; the raw
  secret never reaches swap or a core dump (VAULT's no-leak thesis). Deterministic
  for fixed inputs (stable salt → same key).
- `vault_crypto_seal` / `open` — XChaCha20-Poly1305 with a fresh random 192-bit nonce
  per seal (nonce-misuse-resistant). open verifies the Poly1305 tag BEFORE releasing
  plaintext; on wrong-key/tamper it returns false AND sodium_memzero's pt_out
  (defensive active wipe — fail-closed, no partial leak).
- `vault_secure_alloc/free` — sodium_malloc/free (guard pages + canary + mlock,
  zeroed on free). `_Static_assert`s confirm the size #defines equal libsodium's.
⚠️ **catch 1 RESOLVED:** libsodium chosen; CLAUDE.md §6 amended (`a038979`) to a
per-module allowlist (the old "libcurl only" was already false — CHAFF links
openssl@3+sqlite3). ⚠️ **spec amended (`a038979`):** XChaCha20-Poly1305 replaces
AES-256-GCM (nonce-misuse-resistance, catch B), and key_salt is STABLE not
"per-unlock" (catch A — a per-unlock salt would make stored ciphertext
undecryptable). 44 C Unity (37 engine + 7 crypto); `make all` -Werror clean. (Prior:
VAULT DEFER `165a1de`; slice 1 `655f183`; Anomaly-Tripwire 3D `37c3371`.)

**Skeleton scope check (MANIFESTO §4 — honest accounting):**

Core skeleton v0.2.0 (§7.12) lists: socket server, router, broker, registry,
capability-token issuer, AND a privileged shim (§7.10 / §8.8 — a separate
C/LaunchDaemon for elevated operations, not among the 8 Python `core/` modules).

- Python `core/`: 8/8 modules done ✓
- Privileged shim: Slice 1 NO-OP skeleton done ✓ (peercred-only; secret = Slice 2 gated on code-signing, real ops = Slice 3+)

**ETAP 2 verdict:** Python core skeleton complete. The privileged shim is a
prerequisite for native modules requiring elevated capabilities (VAULT, PURGE,
etc.); its Slice 1 NO-OP skeleton is now done (`e60e8ae`), with the per-boot
secret (Slice 2) gated on code-signing (§5.5) and real ops deferred to Slice 3+.

**`chimera/core/` — 8 of 8 modules implemented:**

- `errors` (§6.5) — JSON-RPC + CHIMERA error codes, RpcError — DONE (`f284891`)
- `envelope` (§6.4) — JSON-RPC 2.0 wire format, parse/serialize, NDJSON — DONE (`6ed8e77`)
- `config` (§6.3, §7, §8) — CoreConfig: paths, defaults, env > toml > defaults hierarchy — DONE (`a6eed2a`)
- `tokens` (§6.9, §8.6 I6) — TokenIssuer: HMAC-SHA256 capability tokens, in-RAM key — DONE (`f9fa508`)
- `broker` (§6.6 + §6.8) — EventBroker: async pub/sub, wildcard topics, drop-oldest backpressure — DONE (`b63916c`)
- `lifecycle` (§7.2 + §7.4 + §7.5) — Lifecycle: 9-state FSM, 16-edge allow-list, heartbeat sweep, restart policy — DONE (`57a99fd`)
- `registry` (§6.7 + §7.2) — Registry: capability store, composes+drives Lifecycle, prefix-split matching, register/deregister events — DONE (`e4a10ba`)
- `server` (§6.3 + §6.2 + §6.9) — Server: two UNIX sockets, core.* dispatch + 4A module routing (internal-id correlation, per-method timeouts, fail-closed), 3B token reissue, event push, graceful shutdown — DONE (`33f2d38`; 4A routing `06bf7cb`). + idea #3 Slice 3B anomaly-relay (`666794d`): `_issue_to_module` (extracted from `_route`, 1:1), `_dispatch_internal` (core-initiated command, in-process authority — NEW; D7 unchanged, not wire-reachable), `_relay_handle`/`_relay_loop` + `RELAY_RULES` ClassVar ({topic→command}); core subscribes itself to the relay topics in a dedicated task (mirrors the sweep task, per-event isolation).

No scaffold remains — all 8 core modules implemented.

**Native modules (`chimera/modules/`) — 4 of 8 started:**

- `chaff` (§5.1) — first native module, working daemon. C17 + ARM64 (Make +
  vendored Unity/cJSON); connects to core, registers + heartbeats, serves chaff.*
  via the 4A router, emits events, generates decoy HTTPS traffic (two pthread
  threads, poll-based IPC, openssl Fernet, SQLite). 46 Unity + 4 integration
  (hermetic). binary -Werror clean. Phase A (profiling) deferred to the
  privileged shim (pf/dtrace = root). — Phase B daemon DONE (`4f443f5`)
- `mirror` (§5.4) — second native module, working daemon. C17 (Make + vendored
  Unity/cJSON, frameworks only — no curl/sqlite/openssl). Connects to core,
  registers (8 methods, 2 events, depends_on=[]), serves mirror.* via the 4A
  router, heartbeats — single inline IPC loop (no pthread; the would-be 2nd
  thread is the gated tap). Engine: Box-Muller gaussian mouse noise, uniform
  timing jitter (clamp ≥0), §3 presets (light/medium/heavy), secure-field
  downgrade to light, fixed-capacity exclusion list, cumulative per-event-type
  stats (§7 — counts only). Config: MIRROR_CONFIG_PATH, non-fatal (defaults if
  missing/malformed). 42 Unity + 4 integration. binary -Werror clean. ipc/jsonrpc
  copied from chaff (D1=C). CGEventTap install + event emission STILL gated
  (code-signing + Accessibility TCC, §6/§9); mirror.enable → -31004; no event
  producer yet (drain_events seam wired, queue empty). — daemon GREEN (`41ef5b1`)
- `oracle` (§5.3) — third native module, FIRST Python module (CHAFF/MIRROR are
  C). observe-first slice: dual-role daemon — conn #1 core.sock (registers,
  serves oracle.{status,observe} via the 4A router, heartbeats, emits
  oracle.baseline.updated) + conn #2 events.sock (core.subscribe chaff.*, D5=b
  allow-list; push-loop into the Observer). One asyncio loop under a TaskGroup;
  shared command writer guarded by an asyncio.Lock. Observer = Mode A learning +
  D11 self-loop guard (oracle.* ignored). BaselineStore = SQLite (events +
  baseline_meta) + Fernet (payload/ctx encrypted at rest), thread-safe
  (check_same_thread=False + RLock), blocking writes off-loaded via
  asyncio.to_thread. advisory-only (D4): no acting methods. Mode B: oracle.classify + oracle.threshold.set via 4A run a real local LLM (llama3.2:1b Q8_0 via Ollama)
  with structured output (format=schema); detector.py + llm.py + prompt.py; context
  = recent_events + summary (baseline-aware); D6 gate (-31004 if Ollama down, Mode A
  survives); malformed → INTERNAL_ERROR (no fake 0.5); threshold meta-backed (0.7);
  status.model from startup probe; classifications_today in-memory. Explainability
  (#1): classify returns {score, reasoning, context_factors[] (LLM-emitted),
  similar_events[] (naive top-3, §5.3 debt repaid)}; derived prompt facts
  (source/type-seen, hour_freq, days_observed) + directive; advisory invariant test.
  Time-Machine (#2): Layer 1 — oracle.query.first_seen + oracle.query.period
  (structured time-range, deterministic, no LLM; query.py TimeMachine, SQL in
  baseline, half-open [start, end)). Layer 2 — oracle.ask: enum-constrained LLM
  intent → dispatch Layer 1 → code-templated {answer, query_used, raw_result};
  "unknown" fallback; raw_result safeguard; ask.py Asker composes TimeMachine
  (Layer 1 stays LLM-free); core oracle.ask:15.0 timeout (NL-12a). Reuses
  core.envelope + core.errors only (D1=c). 58 unit + 14 integration (3 real-Ollama,
  -m ollama). ruff + mypy --strict clean. ORACLE fully done (Mode A + Mode B +
  explainability + time-machine L1+L2). + idea #3 Slice 3C anomaly-emit (`ee794ba`):
  `_handle_classify` emits `oracle.anomaly.detected` (advisory Notification {score,
  threshold, source, type, reasoning}) when score >= get_threshold() (default 0.7);
  emit in the CLIENT, detector advisory-pure (untouched); EVENTS += the topic;
  contract 1:1; announce ≠ act (core 3B routes). First client-unit file
  (test_oracle_client.py, +3; FakeDetector/FakeWriter, hermetic). — anomaly-emit
  GREEN (`ee794ba`)
- `tether` (§5.7) — fourth native module, the FIRST and only C++17 module (spec
  §4: ObjC++ bridges CoreBluetooth). Slice 1 = pure-logic ENGINE + daemon-wiring +
  Slice 3A react-entrypoint, all done (engine→daemon staged like MIRROR). Engine:
  EWMA smoothing (α=0.3),
  presence FSM (PRESENT/FRINGE/ABSENT, missed/recover tick counting),
  disappearance classify (FADE / CLEAN_DROP benign / INSTANT_DROP suspicious),
  escalation ladder (grace→L1→L2→L3). Daemon: Monitor.step composes the engine
  units (EWMA→FSM→classify→escalation), emits transition events (present/fringe/
  absent+class/recovered/suspicious) + escalation-on-stage-change while absent;
  daemon_run does core.register (`tether.*` + 6 real events, depends_on=[]) → inline
  poll loop (serve via 4A, TICK→Monitor.step→emit, 10s heartbeat); make_source
  env-gated (TETHER_SYNTHETIC_RSSI→SyntheticSource else CoreBluetoothSource, gated/
  empty — §4 never fabricates presence). Escalation is EMIT-ONLY — engine evaluate()
  / Monitor.step() return descriptors, never act; core enforces L1 (shim) / L2
  (VAULT) / L3 (PURGE) per spec §5. L3 opt-in, default DISABLED; INSTANT_DROP shifts
  the schedule later (anti-weaponization). Slice 3A react-entrypoint (idea #3):
  tether.heighten/relax + effective_grace_ms(base, heightened) with HEIGHTEN_FACTOR=2
  (grace halved → escalation REQUESTED sooner), shared by commands (status/dry-run) + Monitor; relax is an exact idempotent restore (base grace_ms never mutated);
  Monitor.set_heightened re-arms the ladder with the effective grace (real sync,
  engine class untouched). EMIT-ONLY holds — more sensitive, never more active.
  3A = grace-only (near_threshold-heighten deferred — PresenceMachine not re-armed).
  BLE source (CoreBluetooth) + clock behind
  seams → hermetic; the real source is GATED (Bluetooth HW + TCC). tether.test =
  dry-run (§8, no action/emit). §6 codes (-31002 unknown, -31004 gated pairing),
  tether.* namespace. 48 C++ Unity (35 engine + 10 commands + 10 monitor; extern "C"
  setUp/tearDown) + 5 integration, binary -Werror clean. cJSON vendored; jsonrpc/ipc
  are fresh C++ but jsonrpc.c remains the 4th copy (TE-7b deliberate debt). GATED/
  pending: CoreBluetooth .mm source (prod empty), IRK/Keychain pairing (= VAULT
  entitlement blocker), real L1/L2/L3 effects (no live consumer until shim ops /
  VAULT / PURGE exist). — Slice 3A heighten/relax GREEN (`994a5c4`)
- `vault` (§5.6) — FIFTH native module, C17 (joins the CHAFF/MIRROR C lineage; not
  Python/C++). State-gated encrypted storage: the decryption key materializes only
  when an operator-authored policy evaluates ALLOW against the current context (time
  / presence / module-state) — not key-gated (§2). Slice 1 = the PURE policy DSL
  engine: lexer (idents/numbers/"strings"/operators/punct) + recursive-descent
  parser (or>and>not>primary → AST: allow_when expression + optional relock_after) + typed evaluator (numeric < <= > >= == != between; enum/string == != in;
  and/or/not/parens). ⚠️ fail-closed tri-state {TRUE,FALSE,ERROR}: NULL policy /
  unknown variable / type mismatch / not-running-module value (no explicit `unknown`
  opt-out) → ERROR, propagates through not/and/or, NEVER → ALLOW; not-TRUE = DENY
  (the security heart, §4). Verdict is the FULL three-way ALLOW/DENY/DEFER:
  `vault_decide` adds temporal projection (`165a1de`) — base FALSE → brute-force
  step a context copy forward (advance_hour 1h, DEFER_CAP_STEPS=168 / 7 days) to the
  first ALLOW → {DEFER, step×3600}; non-time vars frozen so a block time can't lift
  → DENY; ERROR never projected. `vault_eval` stays the instantaneous ALLOW/DENY
  (slice-1 contract intact, no test-fit). 1h resolution (day_of_month/boot-second =
  tail). relock_after parsed (min×60/hour×3600), not scheduled.
  CRYPTO (`e82f69b`, libsodium — first VAULT external dep, pure-C phase ends): Argon2id
  MODERATE derive (password = master_secret‖policy_hash, secure-mem + immediate wipe),
  XChaCha20-Poly1305 seal/open (192-bit random nonce, fail-closed verify+wipe), sodium
  secure memory (guard+canary+mlock). catch 1 RESOLVED (libsodium; §6 amended). Spec
  amended: XChaCha20 over AES-GCM (catch B) + stable key_salt (catch A).
  44 C Unity (6 lexer + 6 parser + 9 evaluator + 6 fail_closed + 3 relock + 7 decide + 7 crypto), `make all` -Werror clean. GATED/deferred: Keychain/Secure-Enclave
  master secret (entitlements), mount_tmpfs (catch 2 — root), kqueue relock, IPC/daemon
  (catch 3 — jsonrpc). vault.lock (§6) is the TETHER L2 escalation target.
  — slice 1 `655f183` + DEFER `165a1de` + crypto `e82f69b`
- `common` (`modules/common/`) — NOT an organ: the SHARED jsonrpc unit (JE-1
  extract). `jsonrpc.{h,c}` + `.gitignore`; canonical `jsonrpc_result_t {OK=0,
  ERR=-1, ERR_PARSE=-2}`, `extern "C"` guard. All 4 native consumers
  (chaff/mirror/shim/tether) link it, compiled per-consumer with that module's
  STRICT flags (cJSON-agnostic — the consumer's -I supplies cJSON). VAULT daemon =
  next (first NEW) consumer. — JE-1 done (24cf41f/611c16c/c25dfec/2245f09)
- `pulse` (`modules/pulse/`) — STARTED (NOT complete): scoring slice 1 (`d9b0a42`) + baseline store slice 2 (`bef89a6`) + assess wiring slice 3 (`54b2751`) + temporal group B (`abd2bf3`) + daemon (`44280d2`) + mode.changed emission (`76e9955`) + danger-registry (`b87be5a`) + §6 finishers calibrate/pulse.error (`53547ad`). §5.5 Cognitive Load Monitor — the operator-facing cognitive gate
  ("idea #4"), the only module watching the OPERATOR not the system. pure-Python
  (like ORACLE): `scoring.py` weighted-sum + renorm-to-1.0 + mode `[lo,hi)` + clamp +
  delta-normalize; weights validated (Σ=1.0 else ValueError). ⚠️ fail-safe -> `normal`
  (NEVER block; autonomy §8, opposite of VAULT). Advisory: emits `(score, mode)`; core
  enforces gates. `baseline.py` (slice 2) = encrypted SQLite+Fernet store mirroring
  oracle/baseline.py: per-minute aggregate buckets, 14-day rolling-median over non-gated
  buckets in `[now-14d, now)`, baseline_ready (>=14 distinct days), retention purge;
  signals an open {name:float} dict (no MIRROR fields hardcoded — D8); spec amended first
  (BS-1: retention 7->14d). `assess.py` (slice 3, `54b2751`) bridges store->scoring (group-A baseline-normalize ->
  mean input_delta -> score_and_mode, WS-1..7). `temporal.py` (group B, `abd2bf3`) gives the
  temporal slot its value. 22 + 24 + 10 + 10 = 66 Python unit, all RED->GREEN. DEFERRED (later
  slices): MIRROR
  delta-collection (group A live aggregates),
  ORACLE drift (group C), kqueue idle (group B), IPC/daemon, core gate-enforcement +
  danger-registry + override-phrase (§4/§8).
- ECHO, PURGE — pending (specs in docs/modules/); PULSE STARTED (scoring slice 1, above)

**Idea #3 — Anomaly-Tripwire (ORACLE anomaly → core relay → TETHER react) — COMPLETE:**

✅ COMPLETE (`37c3371`) — CHIMERA's first cross-module reflex, all four slices done
and e2e-confirmed. ⚠️ WIRE-closed, NOT autonomous: the emit is operator-triggered
(oracle.classify); auto-classify-per-event is the tail that makes it fire on its own.

A cross-module wiring: when ORACLE flags an anomaly, core relays it into a TETHER
reaction (tighten the dead-man grace). Path decision = **B (core-relay)**, NOT a
TETHER subscribe — core mediates so TETHER stays ignorant of ORACLE and the star
topology stays clean. (A — TETHER subscribing oracle.anomaly.detected — was
rejected despite the existing ORACLE←chaff.* event-subscription precedent, because
it couples TETHER to ORACLE's topic. The D7 command-plane guard is preserved: only
core, as authority, turns the event into a command.) Slices:

- **3A — TETHER react-entrypoint** — DONE (`994a5c4`): tether.heighten/relax +
  Monitor sync, EMIT-ONLY (sensitivity, not actuation), engine untouched.
- **3B — CORE relay** — DONE (`666794d`): core-internal broker-subscription on
  oracle.anomaly.detected + declarative `RELAY_RULES` {topic→command} +
  `_dispatch_internal` (core issues the command as authority, in-process, no
  caller-id rewrite, D7 unchanged — not wire-reachable); resilient (await-timeout,
  MODULE_OFFLINE if TETHER absent, never crashes the consume loop). `_issue_to_module`
  extracted from `_route` (1:1). Hermetic (synthetic anomaly).
- **3C — ORACLE emit** — DONE (`ee794ba`): `_handle_classify` emits
  oracle.anomaly.detected when score >= threshold (advisory Notification; emit in
  the client, detector untouched). MVP = emit-on-classify; auto-classify-per-event
  = later tail. Hermetic client-unit (no Ollama/sockets).
- **3D — e2e integration** — DONE (`37c3371`): the full chain proven in one e2e
  test (real sockets) — ORACLE classify (high score) → oracle.anomaly.detected →
  broker → core relay → tether.heighten invoked; observable via tether.status
  heightened false→true. FULL spin (core + ORACLE in-process + TETHER binary), only
  seam = FakeDetector score (no Ollama). Confirmation test, not RED→GREEN
  (pass-on-write; 0 production code). 2 tests (happy + threshold-gate negative).

**Privileged shim (`chimera/shim/`) — trust-plane, NOT one of the 8 organs:**

- Top-level `chimera/shim/` (§8.8 / §7.10) — a root LaunchDaemon doing EXACTLY 4
  ops, distinct from the 8 module organs AND from the Python `core/`. C17 (Make +
  vendored Unity/cJSON; jsonrpc copied from the CHAFF/MIRROR lineage). Slice 1
  NO-OP security skeleton: socket SERVER (socket/bind/listen/accept — the inverse
  of the CHAFF/MIRROR clients) + real `getsockopt(SOL_LOCAL, LOCAL_PEERCRED)` →
  xucred uid check (deny-by-default; SS-7 resolver-swap seam lets tests inject a
  mock) + 4-op whitelist (lock/evict/reboot/killall — ALL no-op, F3) + auth-first
  JSON-RPC dispatch (ping/pong, §6 error codes -31007/-31002, shim.* namespace).
  23 Unity, binary -Werror clean. peercred-only (SS-6 — NO per-boot secret this
  slice). `ownership_apply` (SS-0(b) chmod 0660 + chown root:operatorgroup) =
  documented-stub, applied only under the manual `-m privileged` tier (not
  hermetic, SS-7). — Slice 1 GREEN (`e60e8ae`)

`chimera/proto/` — still empty (`.gitkeep`).

**Tooling:** `pyproject.toml` + `uv.lock` + `.venv` (Python 3.13.9); ruff + mypy (strict) + pytest configured. Direct deps: cryptography, pydantic(-settings), **ollama==0.6.2** (§6-allowed; httpx + anyio/certifi transitive). pytest markers: `integration`, `ollama`. Native C deps (Homebrew, fail-fast in each Makefile, §6 allowlist): openssl@3 + sqlite3 (CHAFF), **libsodium (VAULT crypto — XChaCha20-Poly1305/Argon2id/secure-mem)**.

**Tests:**

- Python (pytest, default): 595 passing (31 errors + 41 envelope + 36 config + 35 tokens + 36 broker + 63 lifecycle + 60 registry + 86 server [81 + 5 anomaly-relay 3B] + 12 oracle observe-first + 17 oracle Mode B + 10 oracle explainability + 8 oracle time-machine + 8 oracle NL-ask [7 ask + 1 advisory] + 3 oracle anomaly-emit [3C client-unit] + 22 pulse scoring [slice 1] + 24 pulse baseline store [slice 2] + 10 pulse assess [slice 3] + 10 pulse temporal [group B] + 3 pulse emission [EM] + 5 pulse danger-registry [DR] + 5 pulse finishers [PF] + 8 core gate [GE] + 5 core gate-wiring [GW] + 7 core override [OV] + 3 core gate-override + 5 core override.set [OS] + 6 core gate-hardening [GH] + 3 core entry [SV-1] + 10 core supervisor [SV-2 + T0-c purge_kill] + 8 core CLI [SV-4 + A-4 frozen-plist + shim-check] + 4 core autonomy [SV-5'] (lifecycle owns §7.5 restart) + 3 core mark-lost [CR-1] + 1 core lock [P4c] + 1 core graceful-down [GD] + 3 core tier0 [PURGE T0-a: evict via shim + state wipe] + 3 core purge [T0-b: core.purge -> broadcast + Tier-0])
- Python (integration, marked — `pytest -m integration`): 57 passing (2 core.lock [forwards + LIVE shim] + 8 shim-client [fake + LIVE root shim ping->pong + handshake secret-issuance/caching 2b-iii] + 1 crash-restart [kill echo -> core marks FAILED] + 1 chimera-up [python -m core up brings the organism alive] + 1 supervisor [ECHO+PURGE via dependency waves] + 2 core entry [python -m core serves + clean SIGTERM] + 1 multi-module e2e [ECHO+PURGE+PULSE coexist on one core] + 4 CHAFF + 2 ECHO daemon + 2 PURGE daemon + 4 MIRROR + 5 TETHER + 4 PULSE daemon + 2 PULSE danger + 2 core gate-wiring + 2 anomaly-tripwire e2e [#3 3D: ORACLE+core+TETHER full spin] + 14 ORACLE: 4 observe-first + 3 Mode B hermetic + 2 Time-Machine query + 2 NL-ask + 3 real-Ollama); the 3 real-Ollama skip when Ollama is down. NOTE: real-socket integration needs a short `--basetemp` (AF_UNIX path-too-long, see Open tails)
- Python (ollama, marked — `pytest -m ollama`): 3 passing (subset of integration; real llama3.2:1b)
- Native (CHAFF Unity): 46 passing (7 endpoints + 6 schedule + 6 crypto + 6 db + 10 jsonrpc + 6 commands + 5 generation)
- Native (MIRROR Unity): 42 passing (6 perturb + 6 profile + 5 exclude + 5 stats + 4 rng + 10 jsonrpc + 6 commands)
- Native (shim Unity): 38 passing (13 ops [incl lock/evict/reboot real via injectable actions + killall documented no-op, Slice 3a/3b/3c] + 6 peercred + 2 server + 11 protocol [incl 4 secret-gating + 3 handshake] + 3 secret + 3 attest [fail-closed seams; positive = manual-tier] — per-boot secret + destructive-op gating + shim.handshake secret issuance to a SecCode-attested peer + real lock (pmset) / evict (Keychain, asuser) / reboot (/sbin/reboot), SS-2/3 / 2b / 3a-3c) — separate C trust-plane suite, NOT in pytest
- Native (TETHER C++ Unity): 48 passing (4 ewma + 6 presence + 4 classify + 8 escalation + 6 emit + 10 commands + 10 monitor) — separate C++ suite, NOT in pytest
- Native (VAULT C Unity): 74 passing (6 lexer + 6 parser + 9 evaluator + 6 fail_closed + 3 relock + 7 decide + 7 crypto + 11 commands [VD-1 status + VD-2 create/list + VD-3 create-provisions-KEK + VD-7 delete-removes/no_such_vault + VD-8 policy.update changes/unknown/bad-dsl] + 2 keychain [VD-3 load-or-create] + 15 unlock/mount [VD-4a decision + VD-4b key-derive + VD-4c lock/auto-relock + VD-5 add_file seals + VD-6 decrypt-at-unlock round-trip + VD-8 policy.update refused-with-content/changes-decision + VD-9a unlock-mounts-plaintext + VD-9b lock/relock-unmount] + 2 mount-seam [VD-9a begin/put/end roundtrip + put-without-begin]) — separate C suite, NOT in pytest. VAULT is a live daemon (VD-1..9): create provisions a per-vault Keychain KEK (-> evict has real targets); unlock is state-gated, derives the key, OPENS the sealed files + materialises plaintext into a RAM-backed mount; lock/auto-relock/delete/policy.update unmount (plaintext vanishes); delete drops the vault + evicts its KEK; policy.update re-policies an empty vault. EVERY vault.* method is real; decrypted plaintext is RAM-only. Lone manual-tier path: the real hdiutil RAM-disk mount backend
- Native (ECHO C Unity): 31 passing (9 shaper — budget + flat-wire invariant + burst + clamps; 7 config — defaults + validation + atomic set + budget bridge; 7 stats — padding ratio + decile histogram + surge; 8 commands — echo.* dispatch over jsonrpc) — separate C suite, NOT in pytest
- Native (PURGE C Unity): 35 passing (7 dry-run planner — §8 honest-wipe classify + keys-first tier plan; 9 target registry — add/dedup/remove + plan bridge; 7 config — post-action + marker, atomic set; 12 commands — purge.* dispatch, trigger gated -31004) — separate C suite, NOT in pytest
- Total: 1033 passing (658 default [incl 22 pulse scoring + 24 pulse baseline + 10 pulse assess + 10 pulse temporal + 5 pulse idle [PD-idle-1] + 3 pulse emission + 5 pulse danger-registry + 5 pulse finishers + 8 core gate + 5 core gate-wiring + 7 core override + 3 core gate-override + 5 core override.set + 6 core gate-hardening + 3 core entry + 10 core supervisor + 8 core CLI + 4 core autonomy + 3 core mark-lost + 1 core lock + 1 core graceful-down + 3 core tier0 + 3 core purge + 1 core tether->vault relay + 1 core fan-out relay + 2 core anomaly-obfuscation (chaff+echo) + 1 core de-escalation (recovered stand-down) + 3 ORACLE all-clear (anomaly.cleared hysteresis) + 1 core anomaly-cleared stand-down + 7 core audit store + 2 core audit wiring + 6 core audit surface (render+CLI) + 2 core shim-escalation audit + 3 core pulse->vault reflex + 3 core tether-escalation actuation + 19 core status-view/watch] + 59 integration + 46 CHAFF + 31 ECHO + 35 PURGE + 45 MIRROR + 38 shim + 48 TETHER + 74 VAULT Unity; ollama subset not double-counted)

**Open tails (honest tracking, MANIFESTO §4):**

- Fernet at-rest: CHAFF (C/OpenSSL) and ORACLE (Python `cryptography.Fernet`) share the format but interop is NOT cross-tested (B1 deferred; format-faithful).
- No supervisor — CHAFF, MIRROR, and ORACLE all exit on core-disconnect (graceful, no module auto-restart yet). Core auto-restart is launchd's job (a LaunchAgent KeepAlive plist), which is SEPARATE from the §8.8 privileged-ops shim — §7.10 prose conflates the two.
- Privileged shim (§8.8) — Slice 1 NO-OP skeleton DONE (`e60e8ae`): socket SERVER + peercred (LOCAL_PEERCRED) + 4-op enum + ping/pong; peercred-only (SS-6, no secret); all 4 ops no-op (F3 — ZERO destructive effect). Scope is EXACTLY 4 root ops: lock screen (TETHER L1), evict CHIMERA Keychain (PURGE Tier 0), force-reboot (PURGE post-action), force-killall (Core §7.7 shutdown). §8.8 explicitly never opens sockets, reads files, or runs operator code; only core talks to it (per-boot shared secret — Slice 2).
- Shim Slice 2 (per-boot secret handshake) — gated on code-signing (§5.5 / Finding F2): the in-memory secret only beats a same-uid attacker once core's memory is hardened-runtime-protected. SAME code-signing tail that gates the MIRROR CGEventTap.
- Shim `ownership_apply` (SS-0(b): chmod 0660 + chown root:operatorgroup) = documented-stub — real chmod/chown is a `-m privileged`-tier follow-up (not hermetically testable, SS-7; non-root skeleton binds at umask default).
- Shim real ops (lock/evict/reboot/killall) = Slice 3+ — landed one at a time, destructive (evict/reboot) LAST and only behind the Slice 2 secret; reboot never in autotests (SH-11).
- TETHER (§5.7) — Slice 1 ENGINE (`7269080`) + daemon-wiring (`c2c0882`) + Slice 3A react-entrypoint (`994a5c4`) all done: connect→register→serve via 4A router + TICK→Monitor.step→emit + heartbeat (staged like MIRROR) + tether.heighten/relax. Monitor.step composes the engine units (EMIT-ONLY, never acts). TE-1…TE-10 decisions live in commit history; no separate design-record yet (a docs/TETHER_DESIGN.md is warranted only if it grows).
- TETHER Slice 3A react-entrypoint (`994a5c4`) — tether.heighten/relax flip a `heightened` flag; effective_grace_ms(base, heightened) applies HEIGHTEN_FACTOR=2 (grace halved → escalation requested sooner), shared by commands + Monitor; relax is an exact idempotent restore (base grace_ms never mutated); Monitor.set_heightened re-arms the ladder with the effective grace (real sync — test_heightened_escalates_sooner proves it, not a flag-only stub). Engine class untouched. EMIT-ONLY: more sensitive, never more active. This is idea #3's TETHER leaf — see the Idea #3 section. 3A = grace-only.
- TETHER escalation is EMIT-ONLY (spec §5) — engine evaluate() / Monitor.step() return a decision; CORE enforces L1→shim.lock, L2→VAULT vault.lock, L3→PURGE purge.trigger. TETHER never locks/evicts/reboots itself. Idea #3 (ORACLE anomaly → TETHER react) COMPLETE (`37c3371`): 3A (TETHER react-entrypoint) + 3B (CORE relay) + 3C (ORACLE emit) + 3D (e2e confirmation) all DONE — ORACLE emits oracle.anomaly.detected → core relays → tether.heighten, proven wire-end-to-end, NOT a TETHER subscribe (star topology clean). Path B. ⚠️ WIRE-closed, NOT autonomous — emit is operator-triggered (oracle.classify); auto-classify-per-event is the tail for autonomy. CHIMERA's first cross-module reflex.
- Anomaly-Tripwire e2e test (test_anomaly_tripwire_integration.py, #3 3D) — FULL spin (core + ORACLE in-process + the TETHER C++ binary subprocess) over real sockets; proves the chain by observing tether.status heightened false→true after a high-score oracle.classify. The only seam is FakeDetector score (no Ollama, deterministic). A confirmation test (pass-on-write), NOT RED→GREEN — pure test, 0 production code (all links were already done). Negative test covers the threshold gate (low score → no heighten).
- CORE-initiated command is a NEW capability (idea #3 3B, `666794d`): before, core only forwarded operator commands via `_route`; now `_dispatch_internal` lets core issue a command to a module on its OWN authority. ⚠️ D7 is preserved — `_dispatch_internal` is in-process only, NOT wire-reachable (no JSON-RPC method maps to it), so a module-over-the-wire invoking another module still gets -31007 (NOT_AUTHORIZED). The relay loop is the only caller; resilient (try/except → log, never crashes the consume loop).
- RELAY_RULES is declarative {event_topic → module.method}, a Server ClassVar (METHOD_TIMEOUTS precedent). One rule now: oracle.anomaly.detected → tether.heighten. Adding a tripwire = adding a row, not code. Param-mapping deferred — v1 issues the command with NO params (tether.heighten needs none); a payload→params mapper lands only when a future rule requires it.
- ⚠️ config.set → Monitor grace-sync gap (PRE-EXISTING, not introduced by 3A): tether.config.set mutates rt.escalation.grace_ms (+ presence.near_threshold), but the Monitor holds its OWN `ec_` — only `l3_armed` is mirrored to the live Monitor (set_l3_armed). So a grace change via config.set does NOT reach the running ladder. Slice 3A heighten DOES its part correctly (set_heightened is mirrored after dispatch, beside the l3 sync); config.set's grace/near_threshold sync is a separate tail to fix (mirror config.set → Monitor too, or have Monitor read live config).
- TETHER near_threshold-heighten deferred — Slice 3A is grace-only (the escalation ladder is re-armed per ABSENT, so an effective grace applies naturally). Heightening near_threshold would need the PresenceMachine (constructed once, NOT re-armed) to read live config or be reconstructed — a later tail if anomaly-reaction should also detect absence sooner.
- TETHER GATED / out of slice: CoreBluetooth .mm BLE source (Bluetooth HW + TCC) — make_source returns an EMPTY gated CoreBluetoothSource in production (no synthetic fallback off TETHER_SYNTHETIC_RSSI — §4 never fabricates presence); IRK/companion pairing in Keychain/Secure Enclave (the SAME entitlement blocker as VAULT); real L1/L2/L3 effects (core-enforced downstream — L2 needs VAULT, L3 needs PURGE, neither built). The escalation L1/L2/L3 events have no live consumer until shim ops / VAULT / PURGE exist.
- ✅ TE-7b (4 jsonrpc copies, chaff→mirror→shim→tether) — RESOLVED by the JE-1 extract (chaff `24cf41f` pilot + mirror `611c16c` + shim `c25dfec` + tether `2245f09`). The 4 copies are now ONE canonical `modules/common/jsonrpc.{h,c}`; drift eliminated (each was byte-identical modulo its `<MOD>_result_t` namespace — proven per migration by normalized-diff = only the top comment). C++ tether links the C unit via the common header's `extern "C"` (compiled C `clang -std=c17`, linked clang++). No longer a debt.
- AF_UNIX path-too-long (env, NOT code) — real-socket integration (server `TestRealSocket*`, MIRROR, TETHER) binds UNIX sockets under pytest tmp_path; on macOS the default `TMPDIR` (`/var/folders/.../T`, ~48 chars) + pytest dirs + long test names exceeds the ~104-char `AF_UNIX` limit → 18 default `test_server.py` failures + integration breakage. Fix is ENV: `TMPDIR=/tmp/t` for default, `--basetemp=/tmp/tt` for `-m integration`. Confirmed artifact (438 default + 5 TETHER integration green with short paths). Future: a conftest could pin a short socket dir.
- Packet-plane root is a SEPARATE track, NOT the §8.8 shim: CHAFF Phase A (pf/dtrace) and ECHO (pfctl/BPF/raw socket) need packet-level root, which §8.8 forbids — future §8 amendment or a dedicated packet-helper. CHAFF code returns required_capability='privileged_shim' for profile.*, but §8.8 grants no such capability — spec gap to resolve before that path unblocks.
- ⚠️ VAULT has TWO blockers (CORRECTED — the design-pass caught that the earlier "blocker = entitlements, NOT root" claim was wrong): (1) **entitlements** — Keychain / Secure-Enclave + TCC + code-signing — for the per-vault master secret (the §8.8 shim does not grant this; it only evicts Keychain for PURGE); AND (2) **root** — `mount_tmpfs` exists on this macOS (`/sbin/mount_tmpfs`, Darwin 25) but `mount(2)` needs root, so VAULT's tmpfs mount is privileged. Resolve at the mount-slice: a shim op, an hdiutil `ram://` alternative, or a dedicated helper. The earlier single-blocker claim is retracted.
- VAULT slice 1 (policy DSL engine, `655f183`) + DEFER (`165a1de`) + crypto (`e82f69b`) DONE — evaluator (full ALLOW/DENY/DEFER, fail-closed) + crypto engine (XChaCha20-Poly1305 + Argon2id + secure-mem). `vault_eval` stays the instantaneous ALLOW/DENY (slice-1 contract, 30 tests intact); `vault_decide` is the DEFER entrypoint (no test-fit). The crypto slice ended the pure-C phase (libsodium, deliberately). Remaining slices, ALL gated/platform: Keychain/Enclave master secret (entitlements), mount (catch 2 — root), kqueue relock, IPC/daemon (catch 3 RESOLVED — `modules/common/jsonrpc` extracted (JE-1); the daemon-slice now just LINKS common, no copy). The crypto engine is the foundation; the gated pieces sit on top. ⚠️ daemon-slice UNBLOCKED on jsonrpc, but still gated on Keychain/Enclave master secret + mount (catch 2 — root) — NOT closed.
- VAULT DEFER precision is 1h (the context's finest clock field is `hour`) → defer_seconds is always a multiple of 3600; day_of_month rolls naively (no month calendar) and boot-second projection is coarse, both bounded by the 7-day cap (DEFER_CAP_STEPS=168). Finer resolution would need a minute/second field in the context — a documented tail.
- ✅ VAULT catch 1 — RESOLVED (`a038979` + `e82f69b`): libsodium chosen (Argon2id + XChaCha20-Poly1305 + first-class secure memory); CLAUDE.md §6 amended to a per-module C allowlist (the old "libcurl only" was already false — CHAFF links openssl@3+sqlite3). CommonCrypto rejected (PBKDF2-only = KDF downgrade); openssl@3 was a viable zero-new-dep runner-up but libsodium's secure-memory + spec intent won. No longer open.
- ✅ VAULT spec corrections — RESOLVED in spec (`a038979`, not just code): catch A (key_salt was "rotated per unlock" → STABLE, stored in metadata, rotated only on re-encrypt — a per-unlock salt makes stored ciphertext undecryptable) and catch B (nonce was unspecified → 192-bit random per seal, stored). AEAD changed AES-256-GCM → XChaCha20-Poly1305 with the rationale recorded in-spec. The spec is now truthful.
- VAULT crypto fail-closed + no-leak (`e82f69b`): the raw master secret lives only in sodium_malloc secure memory during derive and is wiped immediately (no swap / core-dump leak — VAULT's thesis, in code). open verifies the Poly1305 tag before releasing plaintext and actively sodium_memzero's pt_out on any failure (wrong key / tamper).
- ⭐ VAULT tamper-test assertion corrected (`e82f69b`) — NOT test-fitting (same class as TETHER's test_present_from_fringe: impl design-correct, the test encoded the wrong post-condition). The RED test asserted a specific sentinel byte survived after a failed open (out[0]==0xAA), but the agreed defensive active-wipe (design-pass nuance 3) zeroes pt_out on failure. The real invariant is "no plaintext leak", not a sentinel — corrected to `memcmp(out, pt, ptlen) != 0` (impl-agnostic: holds whether wiped to 0 or left untouched).
- ✅ VAULT catch 3 — jsonrpc 5th copy — RESOLVED: `modules/common/jsonrpc` now EXISTS (JE-1 extract). VAULT's daemon-slice will LINK common as the FIRST new consumer (D1=C done), never a 5th copy. The trigger fired ahead of VAULT — the extract was done proactively across the existing 4 modules.
- vault.lock (§6) is the TETHER L2 escalation target — when VAULT's daemon + vault.lock land, core can enforce TETHER L2 (tether.escalation → vault.lock), giving #3's L2 a live consumer (currently L2/L3 escalation events have none). Nuance: vault.lock takes {vault_id}; routing an escalation to it means "lock the currently-open vault" — a downstream wiring detail for that slice.
- 0 of 8 native modules NOT started — ALL 8 ORGANS UNDERWAY. CHAFF + MIRROR + ORACLE done; PURGE started (dry-run planner `1481d6d` + target registry `aea7b86` + config `811a261` + command dispatch `76b7b10` + socket loop `3acf1f7` — LIVE registered module (honest-wipe classify + tier plan + Tier-2 list + serves `purge.*` over the wire); ⚠️ real destruction (trigger -31004; Keychain/Mach VM/dc zva/libsodium) gated); ECHO started (shaper `ca06b25` + config `2f381ce` + stats `a0a8014` + command dispatch `c89844d` + socket loop `b223236` — LIVE registered module (register + serve `echo.*` over the wire); ⚠️ real pf/BPF shaping still gated); TETHER started (engine + daemon-wiring + Slice 3A); VAULT started (policy + DEFER + crypto; Keychain/mount/daemon gated); PULSE started (scoring slice 1 `d9b0a42` + baseline store slice 2 `bef89a6` + assess wiring slice 3 `54b2751` + temporal group B `abd2bf3` + daemon `44280d2` + mode.changed emission `76e9955` + danger-registry `b87be5a`; ⚠️ NOT complete — LIVE module (registers, serves pulse.* incl danger-registry, emits pulse.mode.changed) but live signal collection (MIRROR group-A / kqueue idle / ORACLE drift) STILL gated (§6 method surface COMPLETE incl calibrate + pulse.error `53547ad`) + core gate-enforcement — DECISION (`core/gate.py` `7d6c8fa`) + LIVE WIRING (`fbe64cc`: block/delay in `_route` + mode-track + danger-refresh) done + override-phrase storage (`3564968`: PBKDF2 store, gate honors `_override`, secret stripped) done + operator set-phrase (`22aebc7`: core.override.set, surface-only) done; ⚠️ confirm-dialog (surface) + external-OS gating (CLI/shell) + live registry-refresh still deferred; change-requires-current DONE `db19bd5`).
- MIRROR CGEventTap install — GATED on code-signing + Accessibility TCC (§6/§9); mirror.enable returns -31004 until then. The code-signing tail is now shared across MIRROR (tap), shim Slice 2 (secret in hardened-runtime memory), and TETHER (CoreBluetooth TCC + IRK in Keychain).
- MIRROR no event producer yet — daemon wiring done, but drain_events is only a forward-compat seam (queue empty); events ship when the tap lands.
- MIRROR → PULSE aggregate-event gap (D8) — PULSE expects a periodic aggregate event MIRROR doesn't yet define; address at PULSE time.
- jsonrpc — ✅ EXTRACTED to `modules/common/` (JE-1; see the resolved TE-7b tail). ipc is NOT extracted: it diverges by role/language — chaff/mirror have a C client `ipc.c`, tether a C++ `ipc.cpp`, shim has no ipc (inline socket server). ipc stays per-module; only jsonrpc was the clean shared target.
- ORACLE classify is baseline-aware and explainable: returns {score, reasoning, context_factors[], similar_events[]}; advisory — ⚠️ boundary EVOLVED at 3C (`ee794ba`): classify now ANNOUNCES an advisory event (oracle.anomaly.detected) on a threshold breach (score >= get_threshold()), but still never ACTS (announce ≠ act). ORACLE cannot invoke another module (D7); core (3B) routes the event to tether.heighten. Consistent with the pre-existing oracle.baseline.updated emit. The emit lives in the client (_handle_classify), so the detector stays advisory-pure (returns data, mutates nothing — test_oracle_advisory still holds).
- ORACLE classifications_today is in-memory and approximate (no day-rollover).
- ORACLE mid-call Ollama death surfaces as a generic error, not -31004 (startup probe + per-ConnectionError catch cover the typical down cases).
- ORACLE similar_events is naive recency (top-3 same source+type) — embeddings-based similarity is v2 (TODO).
- ORACLE explainability deferred: oracle.explain (separate method) + confidence field (EP-2 enriched classify instead).
- ORACLE next slices: oracle.anomaly.detected emission DONE (3C, emit-on-classify MVP); remaining — auto-classify-per-event (Observer classifies each observed event via the LLM and emits without an operator call — deferred: an LLM call per event is expensive + D6 Ollama-gated) + oracle.model.swap (similar_events debt already repaid naive).
- ORACLE 3C emit-on-classify is operator-triggered (fires only on an oracle.classify call). The Mode A learning path (Observer) does NOT auto-classify — so no anomaly events flow without an operator invoking classify yet; auto-classify-per-event is the tail that makes the tripwire autonomous.
- First ORACLE client-unit file (test_oracle_client.py, 3C) — exercises the emit-side (`_handle_classify`) hermetically via FakeDetector (fixed score, no Ollama) + FakeWriter (captures frames, no socket). Distinct from the 0.42 FakeDetector in test_oracle_integration. Earlier client behaviour was only covered via integration (real sockets); this is the first hermetic client-level unit.
- ORACLE Time-Machine Layer 2 (NL ask) DONE — oracle.ask: enum-intent → Layer 1 dispatch → code-templated answer; "unknown" fallback.
- ORACLE NL-ask: enum stops invented queries but NOT semantic mis-routing (1B answered "whatsapp" to a "chaff" question); raw_result is the transparent safeguard.
- ORACLE Layer 2 LLM-narration deferred (code-template now; richer narration + timeout re-check next); trend/compare/new_since routing deferred.
- ORACLE first core touch: core/server.py METHOD_TIMEOUTS += oracle.ask:15.0 (NL-12a, data-driven cold ~4.4s).
- ORACLE baseline.export (§5.3 spec-debt) explicitly deferred (TM-9b) — separate slice.
- ORACLE real event input is CHAFF only — MIRROR emits nothing yet, so chaff.* is the sole live source feeding the baseline.
- ORACLE standalone `python -m oracle` needs modules/oracle on PYTHONPATH (proper editable-package install is a follow-up; `__main__` cannot self-fix the import path).
- ORACLE client.py (D1=c, Python) carries a TODO to extract a shared Python module-client at the 2nd Python module (mirror of the C D1=C duplication).
