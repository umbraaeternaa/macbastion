/* PURGE tier executor (PG-exec). Runs a built plan's enabled tiers in KEY-FIRST order
 * (tier0 -> tier1 -> tier2 -> tier3, §3 — the crown jewels die before bulk work). Tier
 * effects run through injectable seams. LIVE defaults: tier0 removes CHIMERA's registered
 * state files (statefiles.c); tier2 removes the operator's ENCRYPTED targets (unlink) and
 * REFUSES unencrypted ones (§8 honest-wipe — no SSD overwrite theatre); tier3 zeroes
 * registered sensitive buffers in RAM (secrets.c, §5.8). Still honest NO-OP stubs (§4):
 * tier0's Keychain-eviction half and tier1 (VAULT KEK crypto-shred). */
#ifndef PURGE_EXEC_H
#define PURGE_EXEC_H

#include "targets.h" /* purge_targets_t / purge_target_t (pulls in plan.h) */

/* What the executor actually did this run (1 = that keyless tier succeeded; tier2 = counts). */
typedef struct {
    int tier0_done;
    int tier1_done;
    int tier2_shred; /* Tier-2 ENCRYPTED targets actually removed */
    int tier2_skip;  /* Tier-2 unencrypted targets REFUSED (§8 honest-wipe) */
    int tier3_done;
} purge_exec_result_t;

/* A keyless tier action (tier0/1/3): returns 0 on success, nonzero on failure. */
typedef int (*purge_tier_fn)(void);

/* A Tier-2 per-target action: remove ONE encrypted operator target by path.
 * Returns 0 on success (removed), nonzero on failure. */
typedef int (*purge_tier2_fn)(const char *path);

/* Inject a tier action (tests + the real effects); NULL restores the default. */
void purge_set_tier0_action(purge_tier_fn fn);
void purge_set_tier1_action(purge_tier_fn fn);
void purge_set_tier2_action(purge_tier2_fn fn);
void purge_set_tier3_action(purge_tier_fn fn);

/* Execute `plan`'s enabled tiers in key-first order. `targets` is the Tier-2 operator
 * registry: each ENCRYPTED target is removed via the tier2 action, each unencrypted one is
 * REFUSED (counted in tier2_skip, §8). A NULL `targets` disables Tier-2. A NULL `plan` ->
 * an all-zero result. The executor itself destroys nothing — only the injected actions do. */
purge_exec_result_t purge_execute(const purge_plan_t *plan, const purge_targets_t *targets);

#endif /* PURGE_EXEC_H */
