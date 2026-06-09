/* PURGE Tier-2 target registry — RED stub (PR-5). Sentinel returns so the Unity contract
 * fails until GREEN; an honest empty stub (MANIFESTO §4). */
#include <stddef.h>

#include "targets.h"

void purge_targets_init(purge_targets_t *r) {
    (void)r;
}

int purge_target_add(purge_targets_t *r, const char *path, int encrypted) {
    (void)r;
    (void)path;
    (void)encrypted;
    return -42;
}

int purge_target_remove(purge_targets_t *r, const char *path) {
    (void)r;
    (void)path;
    return -42;
}

int purge_target_count(const purge_targets_t *r) {
    (void)r;
    return -1;
}

const purge_target_t *purge_target_at(const purge_targets_t *r, int i) {
    (void)r;
    (void)i;
    return NULL;
}

purge_plan_t purge_plan_targets(const purge_targets_t *r, int tier1_enabled,
                                int tier2_enabled) {
    (void)r;
    (void)tier1_enabled;
    (void)tier2_enabled;
    purge_plan_t p = {-1, -1, -1, -1, -1};
    return p;
}
