/* protocol — JSON-RPC request dispatch for the privileged shim.
 *
 * RED STUB (Slice 1): not implemented — returns NULL for every request, so the
 * protocol tests (ping/pong, op routing, -31007/-31002 error codes) all fail.
 * GREEN builds the responses via jsonrpc_serialize_* using ops_from_method and
 * the `authorized` verdict. */
#include "protocol.h"

char *protocol_dispatch(const char *method, const cJSON *params, const cJSON *id, int authorized) {
    (void)method;     /* RED: GREEN routes shim.ping + the 4-op whitelist. */
    (void)params;     /* RED: unused this slice (structured enum, no free-form params). */
    (void)id;         /* RED: GREEN echoes the id into the response. */
    (void)authorized; /* RED: GREEN emits -31007 when this is 0. */
    return NULL;
}
