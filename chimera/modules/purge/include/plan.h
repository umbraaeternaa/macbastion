/* PURGE dry-run planner — what WOULD be destroyed, destroying nothing (§5.8 §4/§8, PG-2).
 * Pure logic: the purge.test report + the §8 honest-wipe classification. */
#ifndef PURGE_PLAN_H
#define PURGE_PLAN_H

/* §8 honest-wipe: what PURGE would do to a Tier-2 operator target. */
typedef enum {
    PURGE_SHRED = 0,           /* encrypted -> crypto-shred its key (reliable) */
    PURGE_SKIP_UNENCRYPTED = 1 /* unencrypted -> REFUSE; no security theatre on SSD flash */
} purge_action_t;

/* The purge.test dry-run report — what WOULD die. tier0 (CHIMERA secrets) and tier3
 * (RAM/cache zero) are always-on (1); tier1 (VAULT KEKs) is default-on but configurable;
 * tier2 splits the operator targets into crypto-shred vs honestly-skipped counts. */
typedef struct {
    int tier0;
    int tier1;
    int tier2_shred;
    int tier2_skip;
    int tier3;
} purge_plan_t;

/* §8 honest-wipe invariant: encrypted -> SHRED; unencrypted -> SKIP_UNENCRYPTED. */
purge_action_t purge_classify(int encrypted);

/* Build the dry-run plan (destroys NOTHING). target_encrypted[i] != 0 means target i is
 * encrypted. Tier 0 and Tier 3 always run; Tier 1 runs iff tier1_enabled; Tier-2 targets
 * are classified iff tier2_enabled (else ignored entirely). */
purge_plan_t purge_build_plan(const int *target_encrypted, int n_targets,
                              int tier1_enabled, int tier2_enabled);

#endif /* PURGE_PLAN_H */
