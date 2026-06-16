/* exec — the PURGE tier executor. Runs a plan's enabled tiers key-first (§3):
 * tier0 -> tier1 -> tier2 -> tier3.
 *   tier0: LIVE for CHIMERA's state FILES (purge_statefile_remove_all, statefiles.c); the
 *          Keychain-eviction half is intentionally NOT here — it is privileged (see tier1).
 *   tier1: no-op in THIS unprivileged native daemon BY DESIGN — it must never touch the
 *          operator login Keychain. The VAULT KEK crypto-shred is REAL at the privileged
 *          layer: core.purge -> shim.evict (deletes the `com.umbra.chimera` Keychain items,
 *          service-wide) and vault.delete (per-vault). Validated live Day 24: evicting a
 *          throwaway vault's KEK orphaned its ciphertext (unlock -> no_such_vault).
 *   tier2: operator targets — §8 honest-wipe: remove ENCRYPTED ones (their ciphertext is
 *          noise once keys are shredded), REFUSE unencrypted ones (no SSD overwrite theatre).
 *   tier3: LIVE — zeroes registered sensitive buffers in RAM (secrets.c, §5.8). */
#include "exec.h"

#include <errno.h>
#include <stdio.h>
#include <unistd.h>

#include "secrets.h"
#include "statefiles.h"

/* tier1 is a deliberate no-op HERE: crypto-shredding VAULT's Keychain-resident KEK is a
 * PRIVILEGED op (core.purge -> shim.evict, or vault.delete), never the unprivileged native
 * daemon's to perform. Kept as a tier hook so the plan/exec shape stays uniform. */
static int noop_tier1(void) {
    fprintf(stderr, "purge: tier1 KEK crypto-shred is privileged "
                    "(core.purge/vault.delete) — no-op in the native daemon by design\n");
    return 0;
}

/* Tier-2 per-target removal: unlink one ENCRYPTED operator target. Removing an encrypted
 * file is reliable destruction — its ciphertext is noise once the keys are shredded (tier0/1);
 * §8 forbids pretending to overwrite unencrypted SSD data, so only SHRED-classified (encrypted)
 * targets ever reach here. A path already gone counts as removed (best-effort). */
static int shred_target_real(const char *path) {
    return (unlink(path) == 0 || errno == ENOENT) ? 0 : -1;
}

static purge_tier_fn  g_tier0 = purge_statefile_remove_all;
static purge_tier_fn  g_tier1 = noop_tier1;
static purge_tier2_fn g_tier2 = shred_target_real;
/* tier3 is LIVE: the real RAM-wipe over registered sensitive buffers (secrets.c, §5.8). */
static purge_tier_fn  g_tier3 = purge_secret_clear_all;

void purge_set_tier0_action(purge_tier_fn fn) { g_tier0 = fn ? fn : purge_statefile_remove_all; }
void purge_set_tier1_action(purge_tier_fn fn) { g_tier1 = fn ? fn : noop_tier1; }
void purge_set_tier2_action(purge_tier2_fn fn) { g_tier2 = fn ? fn : shred_target_real; }
void purge_set_tier3_action(purge_tier_fn fn) { g_tier3 = fn ? fn : purge_secret_clear_all; }

purge_exec_result_t purge_execute(const purge_plan_t *plan, const purge_targets_t *targets) {
    purge_exec_result_t r = {0, 0, 0, 0, 0};
    if (!plan) {
        return r;
    }
    /* Key-first (§3): tier0 (crown jewels) then tier1 before any bulk work. */
    if (plan->tier0) {
        r.tier0_done = (g_tier0() == 0) ? 1 : 0;
    }
    if (plan->tier1) {
        r.tier1_done = (g_tier1() == 0) ? 1 : 0;
    }
    /* Tier-2: operator targets. §8 honest-wipe — remove ENCRYPTED targets, REFUSE the rest. */
    if (targets != NULL) {
        int n = purge_target_count(targets);
        for (int i = 0; i < n; i++) {
            const purge_target_t *t = purge_target_at(targets, i);
            if (t == NULL) {
                continue;
            }
            if (purge_classify(t->encrypted) == PURGE_SHRED) {
                if (g_tier2(t->path) == 0) {
                    r.tier2_shred += 1;
                }
            } else {
                r.tier2_skip += 1; /* REFUSED — no security theatre on unencrypted SSD (§8) */
            }
        }
    }
    /* Tier-3 RAM/cache zero — always last (§3). */
    if (plan->tier3) {
        r.tier3_done = (g_tier3() == 0) ? 1 : 0;
    }
    return r;
}
