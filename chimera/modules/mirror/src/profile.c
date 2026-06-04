/* profile — RED-B stub. Returns zeroed params / no-op downgrade / NULL names so
 * the preset tests fail honestly. Real spec §3 presets land in GREEN. */
#include "profile.h"

#include <stddef.h>

mirror_profile_params_t profile_params(mirror_profile_t p) {
    (void)p;
    mirror_profile_params_t zero = {0};
    return zero; /* stub: no real presets yet */
}

mirror_profile_t profile_downgrade(mirror_profile_t current, bool is_secure_field) {
    (void)is_secure_field;
    return current; /* stub: never downgrades */
}

const char *profile_to_str(mirror_profile_t p) {
    (void)p;
    return NULL; /* stub */
}

mirror_profile_t profile_from_str(const char *s) {
    (void)s;
    return (mirror_profile_t)(-1); /* stub: always "unknown" */
}
