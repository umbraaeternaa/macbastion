/* secret — per-boot shared secret (§8 Amendment A1, EP-5, mirrors shim SS-3): 32 CSPRNG bytes,
 * hex-encoded; constant-time compare. Held in memory only (zero disk). */
#include "secret.h"

#include <stdlib.h> /* arc4random_buf */

void shaper_secret_generate(char *out) {
    unsigned char raw[32];
    arc4random_buf(raw, sizeof(raw));
    static const char hexd[] = "0123456789abcdef";
    for (int i = 0; i < 32; i++) {
        out[i * 2] = hexd[(raw[i] >> 4) & 0x0f];
        out[i * 2 + 1] = hexd[raw[i] & 0x0f];
    }
    out[SHAPER_SECRET_HEX_LEN] = '\0';
}

int shaper_secret_equal(const char *a, const char *b) {
    /* Constant-time over the full fixed length — no early exit on the first mismatch. */
    unsigned char diff = 0;
    for (int i = 0; i < SHAPER_SECRET_HEX_LEN; i++) {
        diff = (unsigned char)(diff | ((unsigned char)a[i] ^ (unsigned char)b[i]));
    }
    return diff == 0;
}
