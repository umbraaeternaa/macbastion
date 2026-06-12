/* Secure memory wipe (§5.8 RAM erase). The guaranteed-correct C core: a volatile
 * pointer so the zeroing is NOT dead-store-eliminated even when the buffer is freed
 * right after. The ARM64 `dc zva` acceleration lands in a later slice on top of this. */
#include "wipe.h"

void purge_wipe(void *buf, size_t len) {
    if (buf == NULL) {
        return;
    }
    volatile unsigned char *p = (volatile unsigned char *)buf;
    while (len--) {
        *p++ = 0;
    }
}
