/* PURGE dry-run planner — what WOULD be destroyed, destroying nothing (§5.8 §4/§8, PG-2/3).
 * Pure logic: the §8 honest-wipe classification + the keys-first tier plan. */
#include <stddef.h>

#include "plan.h"

purge_action_t purge_classify(int encrypted) {
    /* §8 honest-wipe: only encrypted data can be reliably destroyed (crypto-shred the
     * key); unencrypted SSD data cannot be guaranteed wiped on wear-levelled flash, so
     * PURGE refuses rather than pretend (no security theatre, MANIFESTO §4). */
    return encrypted ? PURGE_SHRED : PURGE_SKIP_UNENCRYPTED;
}

purge_plan_t purge_build_plan(const int *target_encrypted, int n_targets,
                              int tier1_enabled, int tier2_enabled) {
    /* Tier 0 (CHIMERA secrets) and Tier 3 (RAM/cache zero) always run; Tier 1 (VAULT
     * KEKs) is configurable. Tier-2 operator targets are classified only when enabled. */
    purge_plan_t p = {1, tier1_enabled ? 1 : 0, 0, 0, 1};
    if (tier2_enabled && target_encrypted != NULL) {
        for (int i = 0; i < n_targets; i++) {
            if (purge_classify(target_encrypted[i]) == PURGE_SHRED) {
                p.tier2_shred += 1;
            } else {
                p.tier2_skip += 1;
            }
        }
    }
    return p;
}
