/* profile — perturbation presets + password-field downgrade (§5.4 §3). Preset
 * magnitudes are the spec §3 table verbatim. */
#include "profile.h"

#include <string.h>

mirror_profile_params_t profile_params(mirror_profile_t p) {
    switch (p) {
    case MIRROR_PROFILE_LIGHT:
        return (mirror_profile_params_t){.mouse_sigma = 0.5, .click_delta = 5, .dwell_delta = 10,
                                         .flight_delta = 5};
    case MIRROR_PROFILE_HEAVY:
        return (mirror_profile_params_t){.mouse_sigma = 2.0, .click_delta = 30, .dwell_delta = 50,
                                         .flight_delta = 40};
    case MIRROR_PROFILE_MEDIUM:
    default:
        return (mirror_profile_params_t){.mouse_sigma = 1.0, .click_delta = 15, .dwell_delta = 25,
                                         .flight_delta = 20};
    }
}

mirror_profile_t profile_downgrade(mirror_profile_t current, bool is_secure_field) {
    if (!is_secure_field) {
        return current;
    }
    /* min(current, light): enum order light < medium < heavy, so light wins. */
    return current < MIRROR_PROFILE_LIGHT ? current : MIRROR_PROFILE_LIGHT;
}

const char *profile_to_str(mirror_profile_t p) {
    switch (p) {
    case MIRROR_PROFILE_LIGHT:
        return "light";
    case MIRROR_PROFILE_MEDIUM:
        return "medium";
    case MIRROR_PROFILE_HEAVY:
        return "heavy";
    default:
        return NULL;
    }
}

mirror_profile_t profile_from_str(const char *s) {
    if (s) {
        if (strcmp(s, "light") == 0) {
            return MIRROR_PROFILE_LIGHT;
        }
        if (strcmp(s, "medium") == 0) {
            return MIRROR_PROFILE_MEDIUM;
        }
        if (strcmp(s, "heavy") == 0) {
            return MIRROR_PROFILE_HEAVY;
        }
    }
    return (mirror_profile_t)(-1);
}
