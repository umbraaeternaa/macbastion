/* perturb — RED-B stub. Honest no-noise sentinels: returns inputs unchanged so
 * the contract tests link and fail on assertion. Real Box-Muller + uniform
 * jitter land in GREEN. */
#include "perturb.h"

double perturb_gaussian(double sigma, uint64_t *rng_state) {
    (void)sigma;
    (void)rng_state;
    return 0.0; /* stub: no noise */
}

void perturb_mouse(double *dx, double *dy, double sigma, uint64_t *rng_state) {
    (void)dx;
    (void)dy;
    (void)sigma;
    (void)rng_state;
    /* stub: leave the delta unchanged */
}

int perturb_timing(int base_ms, int delta_ms, uint64_t *rng_state) {
    (void)delta_ms;
    (void)rng_state;
    return base_ms; /* stub: no jitter */
}
