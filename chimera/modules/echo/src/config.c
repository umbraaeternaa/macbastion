/* ECHO config core — RED stub (EC-6). Returns sentinels so the Unity contract fails
 * until GREEN; an honest empty stub, no faked logic (MANIFESTO §4). */
#include "config.h"

#include "shaper.h"

echo_config_t echo_config_default(void) {
    echo_config_t c = {-1, -1};
    return c;
}

int echo_config_valid(int target_kbps, int burst) {
    (void)target_kbps;
    (void)burst;
    return -1;
}

int echo_config_set(echo_config_t *cfg, const int *target_kbps, const int *burst) {
    (void)cfg;
    (void)target_kbps;
    (void)burst;
    return -42;
}

long echo_config_budget(echo_config_t cfg, int tick_ms) {
    (void)cfg;
    (void)tick_ms;
    return -1;
}
