/* perturb — pure perturbation math (§5.4 §3). Gaussian mouse noise + uniform
 * timing jitter. All functions take an explicit PRNG state (deterministic per
 * seed) so the engine is testable without the event tap. Scroll is intentionally
 * absent (spec §8 open question — no fake numbers; passthrough until decided). */
#ifndef MIRROR_PERTURB_H
#define MIRROR_PERTURB_H

#include <stdint.h>

/* Box-Muller gaussian deviate: mean 0, standard deviation `sigma`. Deterministic
 * given the rng state (advances it). sigma <= 0 returns 0. */
double perturb_gaussian(double sigma, uint64_t *rng_state);

/* Add independent gaussian noise (std-dev `sigma` px) to a mouse delta in place. */
void perturb_mouse(double *dx, double *dy, double sigma, uint64_t *rng_state);

/* Jitter a timing value: base_ms + a uniform integer in [-delta_ms, +delta_ms],
 * clamped to >= 0. delta_ms <= 0 returns base_ms unchanged. */
int perturb_timing(int base_ms, int delta_ms, uint64_t *rng_state);

#endif /* MIRROR_PERTURB_H */
