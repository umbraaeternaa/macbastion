/* exec — the PURGE tier executor. Runs a plan's enabled tiers key-first (§3):
 * tier0 -> tier1 -> tier3. tier3 is LIVE — its default action is the real RAM-wipe
 * (purge_secret_clear_all: purge_wipe() every registered sensitive buffer, §5.8). tier0
 * (Keychain evict) and tier1 (VAULT KEK crypto-shred) are still honest NO-OP stubs (§4):
 * they record intent and destroy NOTHING until their gated slices land. Tier-2 per-target
 * shred is a later slice; the planned count is carried through from the dry-run plan. */
#include "exec.h"

#include <stdio.h>

#include "secrets.h"

static int noop_tier0(void) {
    fprintf(stderr, "purge: NO-OP tier0 (evict CHIMERA Keychain + state DBs) — skeleton\n");
    return 0;
}
static int noop_tier1(void) {
    fprintf(stderr, "purge: NO-OP tier1 (crypto-shred VAULT KEKs) — skeleton\n");
    return 0;
}

static purge_tier_fn g_tier0 = noop_tier0;
static purge_tier_fn g_tier1 = noop_tier1;
/* tier3 is LIVE: the real RAM-wipe over registered sensitive buffers (secrets.c, §5.8). */
static purge_tier_fn g_tier3 = purge_secret_clear_all;

void purge_set_tier0_action(purge_tier_fn fn) { g_tier0 = fn ? fn : noop_tier0; }
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
