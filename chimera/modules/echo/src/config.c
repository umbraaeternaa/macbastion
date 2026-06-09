/* ECHO config core — operator knobs with range validation + atomic partial set
 * (§5 §3, EC-1…EC-4). Pure, no I/O (persistence lives in a later slice). */
#include <stddef.h>

#include "config.h"

#include "shaper.h"

echo_config_t echo_config_default(void) {
    echo_config_t c = {ECHO_DEFAULT_KBPS, ECHO_DEFAULT_BURST};
    return c;
}

int echo_config_valid(int target_kbps, int burst) {
    return target_kbps >= ECHO_MIN_KBPS && target_kbps <= ECHO_MAX_KBPS &&
           burst >= ECHO_MIN_BURST && burst <= ECHO_MAX_BURST;
}

int echo_config_set(echo_config_t *cfg, const int *target_kbps, const int *burst) {
    if (cfg == NULL) {
        return -1;
    }
    /* Resolve the would-be config (NULL = keep current), validate it ALL before
     * touching cfg — so a bad value leaves the config untouched (atomic). */
    int new_target = (target_kbps != NULL) ? *target_kbps : cfg->target_kbps;
    int new_burst = (burst != NULL) ? *burst : cfg->burst_tolerance;
    if (!echo_config_valid(new_target, new_burst)) {
        return -1;
    }
    cfg->target_kbps = new_target;
    cfg->burst_tolerance = new_burst;
    return 0;
}

long echo_config_budget(echo_config_t cfg, int tick_ms) {
    return echo_budget_bytes(cfg.target_kbps, tick_ms);
}
