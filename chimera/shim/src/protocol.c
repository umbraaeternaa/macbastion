/* protocol — JSON-RPC request dispatch for the privileged shim, using the §6
 * CHIMERA error codes (NOT generic JSON-RPC -32601):
 *
 *   any method, unauthorized peer  -> error -31007 (not authorized)   [auth-first]
 *   shim.ping (authorized)         -> {"pong": true}
 *   shim.handshake (authorized + code-sig attested) -> {"secret": "<per-boot>"}
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
#include "secret.h"

static char *ok_noop(const cJSON *id, int did_noop) {
    cJSON *result = cJSON_CreateObject();
    cJSON_AddBoolToObject(result, "ok", 1);
    cJSON_AddBoolToObject(result, "noop", did_noop ? 1 : 0);
    return jsonrpc_serialize_response(id, result);
}

char *protocol_dispatch(const char *method, const cJSON *params, const cJSON *id, int authorized,
                        const char *secret, int attested) {
    /* Auth-first: deny before revealing method existence. */
    if (!authorized) {
        return jsonrpc_serialize_error(id, SHIM_RPC_NOT_AUTHORIZED, "not authorized", NULL);
    }
    if (method && strcmp(method, "shim.ping") == 0) {
        cJSON *result = cJSON_CreateObject();
        cJSON_AddBoolToObject(result, "pong", 1);
        return jsonrpc_serialize_response(id, result);
    }
    /* 2b: issue the per-boot secret ONLY to a code-sig-attested peer (the real core).
     * peercred (authorized) is already checked above; `attested` is the audit-token SecCode
     * verdict. No attestation -> no secret -> destructive ops stay unreachable. */
    if (method && strcmp(method, "shim.handshake") == 0) {
        if (!attested || secret == NULL) {
            return jsonrpc_serialize_error(id, SHIM_RPC_NOT_AUTHORIZED, "not attested", NULL);
        }
        cJSON *result = cJSON_CreateObject();
        cJSON_AddStringToObject(result, "secret", secret);
        return jsonrpc_serialize_response(id, result);
    }
    shim_op_t op = ops_from_method(method);
    if (op == SHIM_OP_UNKNOWN) {
        return jsonrpc_serialize_error(id, SHIM_RPC_CAPABILITY_MISSING, "capability missing", NULL);
    }
    /* SS-2: destructive ops (evict/reboot/killall) require the per-boot secret; the
     * reversible op (lock) and ping do not. No destructive op authed by peercred alone. */
    if (op != SHIM_OP_LOCK) {
        const cJSON *s = params ? cJSON_GetObjectItem(params, "secret") : NULL;
        const char *provided = cJSON_IsString(s) ? s->valuestring : NULL;
        if (secret == NULL || provided == NULL || strlen(provided) != SHIM_SECRET_HEX_LEN
            || !secret_equal(provided, secret)) {
            return jsonrpc_serialize_error(id, SHIM_RPC_NOT_AUTHORIZED, "secret required", NULL);
        }
    }
    int did_noop = 0;
    if (ops_execute(op, &did_noop) != SHIM_OK) {
        return jsonrpc_serialize_error(id, SHIM_RPC_CAPABILITY_MISSING, "capability missing", NULL);
    }
    return ok_noop(id, did_noop);
}
