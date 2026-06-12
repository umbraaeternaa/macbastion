/* PURGE tier executor (PG-exec). Runs a built plan's enabled tiers in KEY-FIRST order
 * (tier0 -> tier1 -> tier3, §3 — the crown jewels die before bulk work). Tier effects run
 * through injectable seams; THIS slice ships honest NO-OP stubs that record intent and
 * destroy NOTHING (an SH-6-style skeleton, MANIFESTO §4). The real tier effects — Keychain
 * eviction (core -> shim), VAULT KEK crypto-shred, dc-zva RAM zeroing — land in later
 * slices behind purge.arm + the per-boot secret, tested on throwaway data first. */
#ifndef PURGE_EXEC_H
#define PURGE_EXEC_H

#include "plan.h"

/* What the executor actually did this run (1 = that tier's action succeeded). */
typedef struct {
    int tier0_done;
    int tier1_done;
    int tier2_shred; /* count of Tier-2 targets crypto-shredded (per-target effect: later) */
    int tier3_done;
} purge_exec_result_t;

/* A tier action: returns 0 on success, nonzero on failure. */
typedef int (*purge_tier_fn)(void);

/* Inject a tier action (tests + the future real effects); NULL restores the no-op stub. */
void purge_set_tier0_action(purge_tier_fn fn);
void purge_set_tier1_action(purge_tier_fn fn);
void purge_set_tier3_action(purge_tier_fn fn);

/* Execute `plan`'s enabled tiers in key-first order. The executor itself destroys nothing —
 * only the injected tier actions do (no-op by default). A NULL plan -> an all-zero result. */
purge_exec_result_t purge_execute(const purge_plan_t *plan);

#endif /* PURGE_EXEC_H */
