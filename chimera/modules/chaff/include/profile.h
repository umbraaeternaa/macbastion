/* CHAFF Phase-A profile loader (§5.1): read the browser-history profile (chaff_profile.py output)
 * into category weights for the weighted decoy pick. Fail-safe — any error leaves the caller's
 * flat weights untouched, so an absent/invalid profile keeps the flat Phase-B behaviour (§4). */
#ifndef CHAFF_PROFILE_H
#define CHAFF_PROFILE_H

#include <stdbool.h>

#include "generation.h" /* CHAFF_NUM_CATEGORIES */

/* Parse a profile JSON string's "categories" object into weights, in CATEGORIES order
 * (news, tech, social, search, dev). Missing keys -> 0.0. Returns false (weights untouched)
 * if the JSON is invalid or has no "categories" object. Pure. */
bool chaff_profile_parse(const char *json, double weights_out[CHAFF_NUM_CATEGORIES]);

/* Load + parse profile.json from `path` (thin I/O over chaff_profile_parse). Returns false if
 * the file is missing / unreadable / invalid — the caller then keeps its flat default. */
bool chaff_profile_load(const char *path, double weights_out[CHAFF_NUM_CATEGORIES]);

#endif /* CHAFF_PROFILE_H */
