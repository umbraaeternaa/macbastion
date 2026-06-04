/* CHAFF — Traffic Obfuscator (§5.1). Umbrella header: version, result codes,
 * and the injectable PRNG used by the pure functions (Sub-D1 hybrid). */
#ifndef CHAFF_H
#define CHAFF_H

#include <stdint.h>

#define CHAFF_VERSION "0.1.0-alpha"

/* Internal return-code idiom (D10). Wire-facing JSON-RPC codes (e.g. -31004)
 * live in commands.h and are emitted only by the command layer. */
typedef enum {
    CHAFF_OK = 0,
    CHAFF_ERR = -1,          /* generic failure */
    CHAFF_ERR_PARSE = -2,    /* malformed input */
    CHAFF_ERR_IO = -3,       /* file / db I/O */
    CHAFF_ERR_CRYPTO = -4,   /* encrypt / decrypt / HMAC */
    CHAFF_ERR_NOTFOUND = -5, /* missing key / category */
} chaff_result_t;

/* xorshift64* — deterministic given a seed (Sub-D1: pass state explicitly to
 * pure functions so tests are reproducible; production seeds from HW RNG). */
static inline uint64_t chaff_rng_next(uint64_t *state) {
    uint64_t x = *state;
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    *state = x;
    return x * 0x2545F4914F6CDD1DULL;
}

#endif /* CHAFF_H */
