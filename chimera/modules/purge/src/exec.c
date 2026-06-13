/* exec — the PURGE tier executor. Runs a plan's enabled tiers key-first (§3):
 * tier0 -> tier1 -> tier3.
 *   tier0: LIVE for CHIMERA's state FILES (purge_statefile_remove_all — unlink() each
 *          registered path, statefiles.c); its Keychain-eviction half is still a no-op.
 *   tier1: honest NO-OP stub (VAULT KEK crypto-shred lands in a later gated slice, §4).
 *   tier3: LIVE — zeroes registered sensitive buffers in RAM (purge_secret_clear_all —
 *          purge_wipe() each, secrets.c, §5.8).
 * Tier-2 per-target shred is a later slice; the planned count is carried from the dry run. */
#include "exec.h"

#include <stdio.h>

#include "secrets.h"
#include "statefiles.h"

static int noop_tier1(void) {
    fprintf(stderr, "purge: NO-OP tier1 (crypto-shred VAULT KEKs) — skeleton\n");
    return 0;
}

/* tier0 is LIVE for state files: purge_statefile_remove_all unlink()s each registered path
 * (statefiles.c). The Keychain-eviction half lands in a later slice. */
static purge_tier_fn g_tier0 = purge_statefile_remove_all;
static purge_tier_fn g_tier1 = noop_tier1;
/* tier3 is LIVE: the real RAM-wipe over registered sensitive buffers (secrets.c, §5.8). */
static purge_tier_fn g_tier3 = purge_secret_clear_all;

void purge_set_tier0_action(purge_tier_fn fn) { g_tier0 = fn ? fn : purge_statefile_remove_all; }
void purge_set_tier1_action(purge_tier_fn fn) { g_tier1 = fn ? fn : noop_tier1; }
void purge_set_tier3_action(purge_tier_fn fn) { g_tier3 = fn ? fn : purge_secret_clear_all; }

purge_exec_result_t purge_execute(const purge_plan_t *plan) {
    purge_exec_result_t r = {0, 0, 0, 0};
    if (!plan) {
        return r;
    }
    /* Key-first (§3): tier0 (the crown jewels) before any bulk work, so an interrupted
     * purge has already destroyed the secrets. A failed tier is recorded, not fatal. */
    if (plan->tier0) {
        r.tier0_done = (g_tier0() == 0) ? 1 : 0;
    }
    if (plan->tier1) {
        r.tier1_done = (g_tier1() == 0) ? 1 : 0;
    }
    r.tier2_shred = plan->tier2_shred; /* carry the planned shred count (per-target: later) */
    if (plan->tier3) {
        r.tier3_done = (g_tier3() == 0) ? 1 : 0;
    }
    return r;
}
