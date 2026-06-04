/* schedule — STUB (RED-B). Real hour bucketing + gaussian jitter land in GREEN. */
#include "schedule.h"

int schedule_hour_bucket(time_t ts) {
    (void)ts;
    return -1; /* TODO(green): gmtime_r -> tm_hour */
}

long schedule_jitter_ms(double base_ms, double sigma, uint64_t *rng_state) {
    (void)base_ms;
    (void)sigma;
    (void)rng_state;
    return 0; /* TODO(green): Box-Muller gaussian, floored at 50 */
}
