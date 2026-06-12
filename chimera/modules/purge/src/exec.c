/* exec — the PURGE tier executor. Skeleton slice: tier actions are honest NO-OP stubs
 * (they record intent on stderr and destroy NOTHING, §4). Order is key-first (§3):
 * tier0 -> tier1 -> tier3. Tier-2 per-target shred is a later slice; the planned count is
 * carried through from the dry-run plan so callers see what WOULD be shredded. */
#include "exec.h"

#include <stdio.h>

static int noop_tier0(void) {
    fprintf(stderr, "purge: NO-OP tier0 (evict CHIMERA Keychain + state DBs) — skeleton\n");
    return 0;
}
static int noop_tier1(void) {
    fprintf(stderr, "purge: NO-OP tier1 (crypto-shred VAULT KEKs) — skeleton\n");
    return 0;
}
static int noop_tier3(void) {
    fprintf(stderr, "purge: NO-OP tier3 (RAM/cache zero via dc zva) — skeleton\n");
    return 0;
}

static purge_tier_fn g_tier0 = noop_tier0;
static purge_tier_fn g_tier1 = noop_tier1;
static purge_tier_fn g_tier3 = noop_tier3;

void purge_set_tier0_action(purge_tier_fn fn) { g_tier0 = fn ? fn : noop_tier0; }
void purge_set_tier1_action(purge_tier_fn fn) { g_tier1 = fn ? fn : noop_tier1; }
void purge_set_tier3_action(purge_tier_fn fn) { g_tier3 = fn ? fn : noop_tier3; }

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
