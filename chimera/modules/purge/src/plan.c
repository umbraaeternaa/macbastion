/* PURGE dry-run planner — RED stub (PG-5). Sentinel returns so the Unity contract fails
 * until GREEN; an honest empty stub, no faked logic (MANIFESTO §4). */
#include "plan.h"

purge_action_t purge_classify(int encrypted) {
    (void)encrypted;
    return (purge_action_t)(-1);
}

purge_plan_t purge_build_plan(const int *target_encrypted, int n_targets,
                              int tier1_enabled, int tier2_enabled) {
    (void)target_encrypted;
    (void)n_targets;
    (void)tier1_enabled;
    (void)tier2_enabled;
    purge_plan_t p = {-1, -1, -1, -1, -1};
    return p;
}
