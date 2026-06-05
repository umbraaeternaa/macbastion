/* protocol — JSON-RPC request dispatch for the privileged shim, using the §6
 * CHIMERA error codes (NOT generic JSON-RPC -32601):
 *
 *   any method, unauthorized peer  -> error -31007 (not authorized)   [auth-first]
 *   shim.ping (authorized)         -> {"pong": true}
 *   shim.{lock,evict,reboot,killall} (authorized) -> {"ok":true,"noop":true}
 *   unknown method (authorized)    -> error -31002 (capability missing)
 *
 * Auth is checked first so an unauthorized peer learns nothing about which
 * methods exist. `authorized` is the peercred verdict computed by the caller;
 * the dispatcher never touches the socket. */
#include "protocol.h"

#include <stddef.h>
#include <string.h>

#include "jsonrpc.h"
#include "ops.h"

static char *ok_noop(const cJSON *id, int did_noop) {
    cJSON *result = cJSON_CreateObject();
    cJSON_AddBoolToObject(result, "ok", 1);
    cJSON_AddBoolToObject(result, "noop", did_noop ? 1 : 0);
    return jsonrpc_serialize_response(id, result);
}

char *protocol_dispatch(const char *method, const cJSON *params, const cJSON *id, int authorized) {
    (void)params; /* structured enum only — no free-form params this slice. */

    /* Auth-first: deny before revealing method existence. */
    if (!authorized) {
        return jsonrpc_serialize_error(id, SHIM_RPC_NOT_AUTHORIZED, "not authorized", NULL);
    }
    if (method && strcmp(method, "shim.ping") == 0) {
        cJSON *result = cJSON_CreateObject();
        cJSON_AddBoolToObject(result, "pong", 1);
        return jsonrpc_serialize_response(id, result);
    }
    shim_op_t op = ops_from_method(method);
    if (op == SHIM_OP_UNKNOWN) {
        return jsonrpc_serialize_error(id, SHIM_RPC_CAPABILITY_MISSING, "capability missing", NULL);
    }
    int did_noop = 0;
    if (ops_execute(op, &did_noop) != SHIM_OK) {
        return jsonrpc_serialize_error(id, SHIM_RPC_CAPABILITY_MISSING, "capability missing", NULL);
    }
    return ok_noop(id, did_noop);
}
