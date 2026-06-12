/* wipe — secure memory zeroing (§5.8 RAM erase). The guaranteed-correct C core:
 * overwrites a buffer with zeros in an optimization-resistant way (the writes survive
 * dead-store elimination even when the buffer is freed right after — the whole point of
 * a secure wipe). The ARM64 `dc zva` acceleration lands in a later slice on top of this. */
#ifndef PURGE_WIPE_H
#define PURGE_WIPE_H

#include <stddef.h>

/* Securely overwrite [buf, buf+len) with 0x00. A NULL buf or len==0 is a no-op. */
void purge_wipe(void *buf, size_t len);

#endif /* PURGE_WIPE_H */
