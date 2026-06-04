/* profile — perturbation profile presets + password-field downgrade (§5.4 §3).
 * Presets are hardcoded here (Sub-M2); config.json only selects the active one. */
#ifndef MIRROR_PROFILE_H
#define MIRROR_PROFILE_H

#include <stdbool.h>

typedef enum {
    MIRROR_PROFILE_LIGHT = 0,
    MIRROR_PROFILE_MEDIUM = 1,
    MIRROR_PROFILE_HEAVY = 2,
} mirror_profile_t;

/* Default per spec §3 ("Default profile: medium"). */
#define MIRROR_PROFILE_DEFAULT MIRROR_PROFILE_MEDIUM

/* Per-event perturbation magnitudes for a profile (spec §3 preset table). */
typedef struct {
    double mouse_sigma; /* Gaussian std-dev added to mouse delta, px */
    int click_delta;    /* uniform +/- bound on click press/release timing, ms */
    int dwell_delta;    /* uniform +/- bound on key-hold duration, ms */
    int flight_delta;   /* uniform +/- bound on inter-key gap, ms */
} mirror_profile_params_t;

/* Preset parameters for a profile (spec §3 table). */
mirror_profile_params_t profile_params(mirror_profile_t p);

/* Password-field downgrade (spec §3): on a secure field the effective profile is
 * min(current, light) — i.e. forced to light. Otherwise `current` is unchanged. */
mirror_profile_t profile_downgrade(mirror_profile_t current, bool is_secure_field);

/* Wire name <-> enum. to_str returns a static string ("light"/"medium"/"heavy")
 * or NULL on an invalid enum. from_str returns the enum or (mirror_profile_t)(-1)
 * on an unknown name. */
const char *profile_to_str(mirror_profile_t p);
mirror_profile_t profile_from_str(const char *s);

#endif /* MIRROR_PROFILE_H */
