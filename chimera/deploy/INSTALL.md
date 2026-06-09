# CHIMERA — Local Install & Code-Signing (self-signed)

> The platform keystone. Local-first, self-signed, no Apple account, no cloud.
> You run every step here yourself — nothing in this folder is run by CI or by core.
> SIP and FileVault stay ON throughout.

CHIMERA's privileged + TCC-gated capabilities (the shim's 4 root ops, MIRROR's
CGEventTap, TETHER's CoreBluetooth, PURGE's Keychain eviction) only work against a
**signed** binary with a **stable identity** — TCC grants and the per-boot secret
(SHIM.md F2/SS-4) attach to that identity. This document gets you there.

---

## Step 1 — Code-signing identity + sign the shim  (P1)

macOS will not let `codesign` use a self-signed cert until it is **trusted**, and trust
cannot be scripted. So the identity is created ONCE via the GUI (it is then auto-trusted,
because it is your own self-signed root):

1. Open the real **Keychain Access** app. On recent macOS it is hidden behind the new
   **Passwords** app — do NOT use "Passwords". Open Keychain Access via
   **Finder → Go → Utilities → Keychain Access**, or:
   ```bash
   open "/System/Applications/Utilities/Keychain Access.app"
   ```
2. Menu bar (with Keychain Access focused): **Keychain Access → Certificate Assistant →
   Create a Certificate…**
   - **Name:** `CHIMERA Local`
   - **Identity Type:** `Self Signed Root`
   - **Certificate Type:** `Code Signing`
   - **Create → Continue (past the self-signed warning) → Done**.
3. Sign the binary:
   ```bash
   cd ~/Projects/macbastion/chimera
   bash deploy/sign.sh shim/chimera-shim
   ```
   Expect `[ok] signed + verifies`. (`sign.sh` only SIGNS — it does not create certs.)

Verify yourself:

```bash
codesign --verify --verbose=2 shim/chimera-shim
codesign --display --entitlements - shim/chimera-shim
```

> Signing is the keystone for PRIVILEGED + TCC-gated ops only. Everything non-privileged
> (the supervisor, `chimera up`, self-heal, all module logic) runs fine UNSIGNED — do this
> step when you actually need the gated capabilities, not before.

**What self-signed gives you:** a stable identity (cdhash) for TCC + a hardened-runtime
signature, on THIS machine. **What it does NOT give:** notarization, Gatekeeper-clean
distribution to other Macs, or remote trust. That is fine — CHIMERA is one machine, one
owner (MANIFESTO §1).

---

## Step 2 — Install the shim as a root LaunchDaemon  (P2)

The shim is the only root component (§7.10 / §8.8: lock screen, evict Keychain, reboot,
force-killall — nothing else). One command installs + bootstraps it:

```bash
make -C shim                          # build the shim binary (if not built)
bash deploy/sign.sh shim/chimera-shim # Step 1, if not already signed
sudo bash deploy/install-shim.sh      # copy -> /usr/local/libexec/chimera, write plist, bootstrap
```

`install-shim.sh` writes `/Library/LaunchDaemons/com.umbra.chimera.shim.plist` with YOUR
console-user UID (so core can reach the root socket, SS-0) and runs `launchctl bootstrap
system`. Remove it any time:

```bash
sudo bash deploy/install-shim.sh --uninstall
```

Before this, the shim only runs by hand under its manual `-m privileged` tier (SHIM.md SH-7/8).

---

## Step 3 — Grant TCC permissions  (P3)

TCC (Transparency, Consent & Control) grants CANNOT be scripted — Apple blocks
programmatic granting on purpose (`tccutil` only *resets*, never grants). You grant them
once, by hand, to the **signed** binary; they persist because the `CHIMERA Local`
identity is stable across rebuilds.

**Prerequisite:** sign the module binaries first (same as the shim):

```bash
bash deploy/sign.sh modules/mirror/mirror modules/tether/tether
```

### MIRROR — Accessibility (CGEventTap)

MIRROR injects humanlike input jitter via `CGEventTap`, which requires **Accessibility**.

1. Start the organism once so MIRROR runs and triggers the prompt: `python -m core up`.
2. The first CGEventTap call raises a system prompt → **Open System Settings** → allow.
   - If no prompt: System Settings → Privacy & Security → **Accessibility** → **+** →
     navigate to `…/modules/mirror/mirror` → enable the toggle.
3. Verify: MIRROR's status should report the tap as active (not `-31004`).

### TETHER — Bluetooth (CoreBluetooth)

TETHER's BLE dead-man needs **Bluetooth**. CoreBluetooth also requires a usage string
(`NSBluetoothAlwaysUsageDescription`) in the binary's `Info.plist` — that is a TETHER
*build* concern (embedded `__info_plist` section), separate from this grant.

1. With TETHER running, the first CoreBluetooth use raises the Bluetooth prompt → allow.
2. Or manually: System Settings → Privacy & Security → **Bluetooth** → enable the TETHER binary.

### When a grant resets

- **Same identity, rebuilt binary** → grant PERSISTS (this is why we use one stable cert).
- **Different identity / unsigned** → grant RESETS; macOS re-prompts.
- To force a clean re-prompt during testing: `tccutil reset Accessibility` /
  `tccutil reset Bluetooth` (resets ALL apps' grant for that service — use deliberately).

---

## Step 4+ — Privileged + gated ops (behind signing)

Once Steps 1–3 hold, these unlock in order (each its own slice, SHIM.md §5.4):

1. shim **per-boot secret** handshake (auth becomes real, not peercred-only) — SS-4.
2. the 4 root ops go live (lock / Keychain-evict / reboot / killall).
3. PURGE real destruction (Keychain evict via shim → Mach VM → ARM64 `dc zva`).
4. ECHO pf/BPF packet shaping — a **separate §8 amendment** (SH-12), not via the shim.

---

## Honest limits

- Self-signed = trusted **only because you said so**, only on this machine. No notarization.
- Every privileged effect is real and irreversible-capable — never test destructive ops
  outside the manual `-m privileged` tier, never in CI.
- macOS updates can reset TCC / re-prompt Gatekeeper; re-verify after a major OS update.
- Read alongside: `docs/SHIM.md` (privileged design), `docs/ARCHITECTURE.md` §8, `docs/OPSEC.md`.
