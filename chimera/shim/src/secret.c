/* secret — per-boot shared secret (SS-3). RED STUB: not implemented (zeros + never-equal),
 * so the Unity contract fails until GREEN. */
#include "secret.h"

#include <string.h>

void secret_generate(char *out) {
    memset(out, '0', SHIM_SECRET_HEX_LEN); /* RED: not random -> two secrets won't differ */
    out[SHIM_SECRET_HEX_LEN] = '\0';
}

int secret_equal(const char *a, const char *b) {
    (void)a;
    (void)b;
    return 0; /* RED: never equal */
}
