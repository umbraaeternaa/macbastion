/* Timing: hour bucketing + gaussian jitter (§5.1 Phase B). */
#ifndef CHAFF_SCHEDULE_H
#define CHAFF_SCHEDULE_H

#include <stdint.h>
#include <time.h>

/* Hour-of-day bucket (UTC, 0..23) for a unix timestamp. UTC is used for
 * deterministic tests; local-hour mapping is the generation layer's concern. */
int schedule_hour_bucket(time_t ts);

/* Gaussian inter-request gap in ms: max(50, gauss(mu=base_ms, sigma)).
 * rng_state is advanced in place (deterministic given a seed). */
long schedule_jitter_ms(double base_ms, double sigma, uint64_t *rng_state);

#endif /* CHAFF_SCHEDULE_H */
