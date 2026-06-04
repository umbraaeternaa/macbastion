/* schedule — UTC hour bucketing + Box-Muller gaussian jitter (§5.1 Phase B). */
#include "schedule.h"

#include <math.h>

#include "chaff.h" /* chaff_rng_next */

#define CHAFF_PI 3.14159265358979323846
#define JITTER_FLOOR_MS 50.0

int schedule_hour_bucket(time_t ts) {
    struct tm tm;
    gmtime_r(&ts, &tm);
    return tm.tm_hour;
}

/* Uniform double in [0,1) from the top 53 bits of the PRNG. */
static double rng_unit(uint64_t *state) {
    return (double)(chaff_rng_next(state) >> 11) / (double)((uint64_t)1 << 53);
}

long schedule_jitter_ms(double base_ms, double sigma, uint64_t *rng_state) {
    double u1 = rng_unit(rng_state);
    double u2 = rng_unit(rng_state);
    if (u1 < 1e-12) {
        u1 = 1e-12; /* guard against log(0) */
    }
    double z = sqrt(-2.0 * log(u1)) * cos(2.0 * CHAFF_PI * u2);
    double v = base_ms + z * sigma;
    if (v < JITTER_FLOOR_MS) {
        v = JITTER_FLOOR_MS;
    }
    return (long)(v + 0.5);
}
