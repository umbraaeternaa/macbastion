/* protocol — JSON-RPC dispatch for the ECHO packet-shaper (§8 Amendment A1, EP-5). Maps
 * shaper.* methods to the anchor lifecycle, auth-first (the caller's peercred verdict) + a
 * per-boot-secret gate on the privileged pf ops, using the §6 CHIMERA error codes. PURE — it
 * never touches the socket; the caller supplies the `authorized` verdict and the shaper's
 * current per-boot `secret`. */
#ifndef SHAPER_PROTOCOL_H
#define SHAPER_PROTOCOL_H

#include "cJSON.h"

/* §6 RPC error codes (shared CHIMERA contract — same numbers as the shim). */
#define SHAPER_RPC_NOT_AUTHORIZED     (-31007) /* unauthorized peer / missing-or-wrong secret */
#define SHAPER_RPC_CAPABILITY_MISSING (-31002) /* method not in the shaper whitelist */

/* Dispatch one request. `authorized` is the caller's peercred verdict; `secret` is the
 * shaper's current per-boot secret (NULL if none). Returns a malloc'd JSON response string
 * (caller frees), or NULL on allocation failure. Auth-first: an unauthorized peer learns
 * nothing about which methods exist. */
char *shaper_protocol_dispatch(const char *method, const cJSON *params, const cJSON *id,
                               int authorized, const char *secret);

#endif /* SHAPER_PROTOCOL_H */
