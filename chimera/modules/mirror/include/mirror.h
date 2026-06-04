/* MIRROR — Behavioral Noise Injector (§5.4). Umbrella header: version, result
 * codes, and the injectable PRNG used by the perturbation engine.
 *
 * Scope: the perturbation engine + daemon + IPC build and test here. The actual
 * CGEventTap install is GATED on code-signing + Accessibility TCC (§6/§9) and is
 * not exercised by automated tests (MANIFESTO §4 — honest accounting). */
#ifndef MIRROR_H
#define MIRROR_H

#include <stdint.h>

#define MIRROR_VERSION "0.1.0-alpha"

/* Internal return-code idiom. Wire-facing JSON-RPC codes are emitted only by
 * the command layer. */
typedef enum {
    MIRROR_OK = 0,
    MIRROR_ERR = -1,          /* generic failure */
    MIRROR_ERR_PARSE = -2,    /* malformed input */
    MIRROR_ERR_IO = -3,       /* file / socket I/O */
    MIRROR_ERR_NOTFOUND = -5, /* missing key / entry */
} mirror_result_t;

/* xorshift64* — deterministic given a seed (D3: software PRNG for now; the
 * spec's mrs RNDR hardware seed is deferred). */
static inline uint64_t mirror_rng_next(uint64_t *state) {
    uint64_t x = *state;
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    *state = x;
    return x * 0x2545F4914F6CDD1DULL;
}

#endif /* MIRROR_H */
