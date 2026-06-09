/* secret — per-boot shared secret (SS-3): 32 CSPRNG bytes, hex-encoded; constant-time
 * compare. Held in memory only (SS-4). */
#include "secret.h"

#include <stdlib.h> /* arc4random_buf */

void secret_generate(char *out) {
    unsigned char raw[32];
    arc4random_buf(raw, sizeof(raw));
    static const char hexd[] = "0123456789abcdef";
    for (int i = 0; i < 32; i++) {
        out[i * 2] = hexd[(raw[i] >> 4) & 0x0f];
        out[i * 2 + 1] = hexd[raw[i] & 0x0f];
    }
    out[SHIM_SECRET_HEX_LEN] = '\0';
}

int secret_equal(const char *a, const char *b) {
    /* Constant-time over the full fixed length — no early exit on first mismatch. */
    unsigned char diff = 0;
    for (int i = 0; i < SHIM_SECRET_HEX_LEN; i++) {
        diff = (unsigned char)(diff | ((unsigned char)a[i] ^ (unsigned char)b[i]));
    }
    return diff == 0;
}
