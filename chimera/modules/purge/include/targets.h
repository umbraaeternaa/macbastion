/* PURGE Tier-2 target registry — operator-designated destruction targets (§3/§7, PR-1…4).
 * Pure in-memory storage (bounded, no malloc this slice) + a bridge to the dry-run plan. */
#ifndef PURGE_TARGETS_H
#define PURGE_TARGETS_H

#include "plan.h"

#define PURGE_MAX_TARGETS 64
#define PURGE_PATH_MAX 256

typedef struct {
    char path[PURGE_PATH_MAX];
    int encrypted; /* operator/detector-supplied; real detection is gated/platform */
} purge_target_t;

typedef struct {
    purge_target_t items[PURGE_MAX_TARGETS];
    int count;
} purge_targets_t;

void purge_targets_init(purge_targets_t *r);

/* Add a target. Idempotent by path (an existing path updates its encrypted flag, no dup).
 * Returns the new count, or -1 on a NULL/empty/too-long path or when the registry is full. */
int purge_target_add(purge_targets_t *r, const char *path, int encrypted);

/* Remove a target by path (idempotent — no error if absent). Returns the new count. */
int purge_target_remove(purge_targets_t *r, const char *path);

int purge_target_count(const purge_targets_t *r);

/* The target at index i, or NULL if out of range. */
const purge_target_t *purge_target_at(const purge_targets_t *r, int i);

/* Bridge: build the dry-run plan from the registry's targets (PR-4). */
purge_plan_t purge_plan_targets(const purge_targets_t *r, int tier1_enabled, int tier2_enabled);

#endif /* PURGE_TARGETS_H */
