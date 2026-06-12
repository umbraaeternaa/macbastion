/* Secure memory wipe (§5.8 RAM erase). Optimization-resistant: the unaligned head/tail
 * are zeroed through a `volatile` pointer (so the wipe survives dead-store elimination),
 * and the aligned middle is zeroed with the AArch64 `dc zva` block instruction
 * (purge_zva_*, in wipe_zva.S) — fast, cache-line-granular. If `dc zva` is unavailable
 * (DZP set), it falls back to the byte loop for the whole buffer. */
#include "wipe.h"

#include <stdint.h>

void purge_wipe(void *buf, size_t len) {
    if (buf == NULL || len == 0) {
        return;
    }
    volatile unsigned char *p = (volatile unsigned char *)buf;
    size_t bs = purge_zva_blocksize();
    if (bs >= 16) {
        /* byte-wipe the unaligned head up to the next block boundary */
        while (len > 0 && ((uintptr_t)p & (bs - 1)) != 0) {
            *p++ = 0;
            len--;
        }
        /* dc zva the aligned middle, one block at a time */
        while (len >= bs) {
            purge_zva_one((void *)(uintptr_t)p);
            p += bs;
            len -= bs;
        }
    }
    /* byte-wipe the tail (or the whole buffer if dc zva was unavailable) */
    while (len > 0) {
        *p++ = 0;
        len--;
    }
}
