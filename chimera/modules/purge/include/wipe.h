/* wipe — secure memory zeroing (§5.8 RAM erase). The guaranteed-correct C core:
 * overwrites a buffer with zeros in an optimization-resistant way (the writes survive
 * dead-store elimination even when the buffer is freed right after — the whole point of
 * a secure wipe). The ARM64 `dc zva` acceleration lands in a later slice on top of this. */
#ifndef PURGE_WIPE_H
#define PURGE_WIPE_H

#include <stddef.h>

/* Securely overwrite [buf, buf+len) with 0x00. A NULL buf or len==0 is a no-op. */
void purge_wipe(void *buf, size_t len);

/* DC ZVA block size in bytes (read from DCZID_EL0), or 0 if dc zva is unavailable —
 * purge_wipe then falls back to the byte loop. Always a power of two when nonzero. */
size_t purge_zva_blocksize(void);

/* Zero one DC ZVA block at `block` (which must be block-size aligned) via `dc zva`. */
void purge_zva_one(void *block);

#endif /* PURGE_WIPE_H */
