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

```bash
cd ~/Projects/macbastion/chimera
bash deploy/sign.sh shim/chimera-shim
```

First run: no `CHIMERA Local` identity exists, so the script creates a self-signed
code-signing cert in your **login keychain** and stops. Then, ONE manual step:

1. Open **Keychain Access** → login → find **CHIMERA Local**.
2. Double-click it → **Trust** → **Code Signing: Always Trust** → close (Touch ID / password).
3. Re-run `bash deploy/sign.sh shim/chimera-shim` — it now signs + verifies.

Verify yourself:

```bash
codesign --verify --verbose=2 shim/chimera-shim
codesign --display --entitlements - shim/chimera-shim
```

**What self-signed gives you:** a stable identity (cdhash) for TCC + a hardened-runtime
signature, on THIS machine. **What it does NOT give:** notarization, Gatekeeper-clean
distribution to other Macs, or remote trust. That is fine — CHIMERA is one machine, one
owner (MANIFESTO §1).

---

## Step 2 — Install the shim as a root LaunchDaemon  (P2 — script lands next)

The shim is the only root component (§7.10 / §8.8: lock screen, evict Keychain, reboot,
force-killall — nothing else). It runs as a LaunchDaemon.

```bash
# (provided in P2)
sudo cp deploy/com.umbra.chimera.shim.plist /Library/LaunchDaemons/
sudo launchctl bootstrap system /Library/LaunchDaemons/com.umbra.chimera.shim.plist
```

Until then the shim runs by hand under its manual `-m privileged` test tier (SHIM.md SH-7/SH-8).

---

## Step 3 — Grant TCC permissions  (P3 — guide lands next)

These are **System Settings grants**, not entitlements — you grant them to the signed
binary once, and they persist because the identity is stable:

- **MIRROR** (CGEventTap, behavioral noise): System Settings → Privacy & Security →
  **Accessibility** → enable the MIRROR binary.
- **TETHER** (CoreBluetooth dead-man): System Settings → Privacy & Security →
  **Bluetooth** → enable. (TETHER also needs a Bluetooth usage string.)

If you ever rebuild a binary with a DIFFERENT identity, its TCC grant resets — that is
why the stable `CHIMERA Local` identity matters.

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
