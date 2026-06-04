/* generation — pure decision logic for the Phase B loop (§5.1). */
#include "generation.h"

#include "schedule.h"

#define CHAFF_JITTER_SIGMA_MS 300.0 /* §5.1: gauss sigma for inter-request gap */

double generation_target_volume(double mean_requests, double multiplier) {
    return mean_requests * multiplier;
}

bool generation_should_send(double sent_volume, double target_volume) {
    return sent_volume < target_volume;
}

chaff_result_t generation_plan_next(const endpoint_list_t *list, const char *category,
                                    double base_gap_ms, uint64_t *rng_state, gen_plan_t *out) {
    if (!list || !category || !rng_state || !out) {
        return CHAFF_ERR;
    }
    const endpoint_t *e = endpoints_pick(list, category, rng_state);
    if (!e) {
        return CHAFF_ERR_NOTFOUND;
    }
    out->endpoint = e;
    out->jitter_ms = schedule_jitter_ms(base_gap_ms, CHAFF_JITTER_SIGMA_MS, rng_state);
    return CHAFF_OK;
}
