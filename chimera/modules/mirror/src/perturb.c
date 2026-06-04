/* perturb — perturbation math (§5.4 §3). Box-Muller gaussian (same pattern as
 * chaff/schedule.c) for mouse noise; uniform integer jitter for timing. The PRNG
 * state is passed in explicitly so the engine stays deterministic + testable. */
#include "perturb.h"

#include <math.h>

#include "mirror.h" /* mirror_rng_next */

#define MIRROR_PI 3.14159265358979323846

/* Uniform double in [0,1) from the top 53 bits of the PRNG. */
static double rng_unit(uint64_t *state) {
    return (double)(mirror_rng_next(state) >> 11) / (double)((uint64_t)1 << 53);
}

double perturb_gaussian(double sigma, uint64_t *rng_state) {
    if (sigma <= 0.0) {
        return 0.0;
    }
    double u1 = rng_unit(rng_state);
    double u2 = rng_unit(rng_state);
    if (u1 < 1e-12) {
        u1 = 1e-12; /* guard against log(0) */
    }
    double z = sqrt(-2.0 * log(u1)) * cos(2.0 * MIRROR_PI * u2);
    return z * sigma;
}

void perturb_mouse(double *dx, double *dy, double sigma, uint64_t *rng_state) {
    if (dx) {
        *dx += perturb_gaussian(sigma, rng_state);
    }
    if (dy) {
        *dy += perturb_gaussian(sigma, rng_state);
    }
}

int perturb_timing(int base_ms, int delta_ms, uint64_t *rng_state) {
    if (delta_ms <= 0) {
        return base_ms;
    }
    /* uniform integer in [-delta_ms, +delta_ms] */
    uint64_t span = (uint64_t)(2 * delta_ms + 1);
    int offset = (int)(mirror_rng_next(rng_state) % span) - delta_ms;
    int v = base_ms + offset;
    return v < 0 ? 0 : v;
}
