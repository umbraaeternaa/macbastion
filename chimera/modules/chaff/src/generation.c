/* generation — STUB (RED-B). Real decision logic lands in GREEN. */
#include "generation.h"

double generation_target_volume(double mean_requests, double multiplier) {
    (void)mean_requests;
    (void)multiplier;
    return -1.0; /* TODO(green): mean_requests * multiplier */
}

bool generation_should_send(double sent_volume, double target_volume) {
    (void)sent_volume;
    (void)target_volume;
    return false; /* TODO(green): sent_volume < target_volume */
}

chaff_result_t generation_plan_next(const endpoint_list_t *list, const char *category,
                                    double base_gap_ms, uint64_t *rng_state, gen_plan_t *out) {
    (void)list;
    (void)category;
    (void)base_gap_ms;
    (void)rng_state;
    if (out) {
        out->endpoint = NULL;
        out->jitter_ms = 0;
    }
    return CHAFF_ERR; /* TODO(green): endpoints_pick + schedule_jitter_ms */
}
