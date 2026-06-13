/* secrets — registry of sensitive in-memory regions to zero on PURGE tier3 (§5.8 RAM erase).
 * The real tier3 action (purge_secret_clear_all) calls purge_wipe() on every registered region.
 * CHIMERA registers its own key material here (KEKs, the per-boot secret, plaintext buffers) so a
 * fired purge zeroes them in RAM. This touches ONLY registered process memory — nothing on disk,
 * nothing of the operator's files (the safest real tier; tier0/tier1 persistent destruction is
 * separate and gated). The registry is fixed-capacity — no allocation on the purge path. */
#ifndef PURGE_SECRETS_H
#define PURGE_SECRETS_H

#include <stddef.h>

/* Maximum number of regions the registry holds. */
#define PURGE_SECRET_MAX 16

/* Register [buf, buf+len) as a sensitive region to be zeroed on purge.
 * Returns 0 on success; -1 if buf is NULL, len is 0, or the registry is full. */
int purge_secret_register(void *buf, size_t len);

/* purge_wipe() every registered region (the real tier3 action). Always returns 0; an
 * empty registry is a safe no-op. */
int purge_secret_clear_all(void);

/* Number of currently registered regions. */
size_t purge_secret_count(void);

/* Forget all registrations WITHOUT wiping (re-init / test teardown). */
void purge_secret_reset(void);

#endif /* PURGE_SECRETS_H */
