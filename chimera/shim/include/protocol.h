/* Request dispatch for the privileged shim. Turns one parsed JSON-RPC request
 * into a malloc'd response string (caller frees), using the §6 CHIMERA error
 * codes (NOT generic JSON-RPC -32601):
 *
 *   shim.ping                       -> {"pong": true}
 *   shim.{lock,evict,reboot,killall} (authorized) -> {"ok": true, "noop": true}
 *   any method, unauthorized peer   -> error -31007 (not authorized)
 *   unknown method (authorized)     -> error -31002 (capability missing)
 *
 * `authorized` is the peercred verdict computed by the caller (peercred_authorized
 * over the connection). The dispatcher does not itself touch the socket. */
#ifndef SHIM_PROTOCOL_H
#define SHIM_PROTOCOL_H

#include "cJSON.h"

#include "shim.h"

/* Dispatch one request. `authorized` != 0 means the peer passed the peercred
 * check. Returns a malloc'd JSON-RPC response string, or NULL on allocation
 * failure. */
char *protocol_dispatch(const char *method, const cJSON *params, const cJSON *id, int authorized,
                        const char *secret);

#endif /* SHIM_PROTOCOL_H */
