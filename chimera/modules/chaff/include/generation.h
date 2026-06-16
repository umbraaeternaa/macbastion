/* Generation-loop decision logic, isolated from the HTTPS/I/O wiring (§5.1
 * Phase B). These functions are pure so the loop is unit-testable. */
#ifndef CHAFF_GENERATION_H
#define CHAFF_GENERATION_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "chaff.h"
#include "endpoints.h"

#define CHAFF_DEFAULT_MULTIPLIER 10.0
#define CHAFF_NUM_CATEGORIES 5 /* news, tech, social, search, dev (daemon.c CATEGORIES order) */

/* Target decoy volume for an hour = mean_requests * multiplier. */
double generation_target_volume(double mean_requests, double multiplier);

/* Whether more decoys are owed this hour. */
bool generation_should_send(double sent_volume, double target_volume);

typedef struct {
    const endpoint_t *endpoint; /* borrowed from the list */
    long jitter_ms;
} gen_plan_t;

/* Plan the next decoy: pick an endpoint of the category + compute the gap.
 * Pure given rng_state. CHAFF_ERR_NOTFOUND if the category is empty. */
chaff_result_t generation_plan_next(const endpoint_list_t *list, const char *category,
                                    double base_gap_ms, uint64_t *rng_state, gen_plan_t *out);

/* Weighted category pick (Phase-A profile). Returns an index in [0, n) chosen with probability
 * proportional to weights[i]. A NULL / zero / all-non-positive weight vector -> uniform fallback,
 * so an absent profile keeps the flat Phase-B behaviour (§4). Pure given rng_state. */
int chaff_weighted_category(const double *weights, size_t n, uint64_t *rng_state);

#endif /* CHAFF_GENERATION_H */
