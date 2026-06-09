/* ECHO shaper core — RED stub (ES-6). Returns sentinels so the Unity contract fails
 * until GREEN; an honest empty stub, no faked math (MANIFESTO §4). */
#include "shaper.h"

long echo_budget_bytes(int target_kbps, int tick_ms) {
    (void)target_kbps;
    (void)tick_ms;
    return -1;
}

echo_decision_t echo_shape(long queued, long budget, long burst) {
    (void)queued;
    (void)budget;
    (void)burst;
    echo_decision_t d = {-1, -1};
    return d;
}
