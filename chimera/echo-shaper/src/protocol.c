/* protocol — JSON-RPC dispatch for the ECHO packet-shaper (§8 Amendment A1, EP-5). Auth-first
 * (peercred verdict), then the shaper whitelist; every pf op is privileged and gated on the
 * per-boot secret (peercred alone is NOT enough). §6 error codes. PURE — never touches the
 * socket. shaper.pace is an honest no-op for now: the dummynet pipe (set by anchor.load) already
 * shapes IN KERNEL, so the userspace pacer the spec describes is a later (possibly vestigial) slice. */
#include "protocol.h"

#include <stddef.h>
#include <string.h>

#include "anchor.h"
#include "jsonrpc.h"
#include "shaper.h"

static char *ok_response(const cJSON *id) {
    cJSON *result = cJSON_CreateObject();
    cJSON_AddBoolToObject(result, "ok", 1);
    return jsonrpc_serialize_response(id, result);
}

char *shaper_protocol_dispatch(const char *method, const cJSON *params, const cJSON *id,
                               int authorized, const char *secret) {
    /* Auth-first: deny before revealing which methods exist. */
    if (!authorized) {
        return jsonrpc_serialize_error(id, SHAPER_RPC_NOT_AUTHORIZED, "not authorized", NULL);
    }
    if (method != NULL && strcmp(method, "shaper.ping") == 0) {
        cJSON *result = cJSON_CreateObject();
        cJSON_AddBoolToObject(result, "pong", 1);
        return jsonrpc_serialize_response(id, result);
    }
    shaper_op_t op = shaper_op_from_method(method);
    if (op == SHAPER_OP_UNKNOWN) {
        return jsonrpc_serialize_error(id, SHAPER_RPC_CAPABILITY_MISSING, "capability missing",
                                       NULL);
    }
    /* Every pf op is privileged -> require the per-boot secret (NOT peercred alone). The
     * constant-time secret compare is a later slice (D); a plain match suffices for the seam. */
    const cJSON *s = params ? cJSON_GetObjectItem(params, "secret") : NULL;
    const char *provided = cJSON_IsString(s) ? s->valuestring : NULL;
    if (secret == NULL || provided == NULL || strcmp(provided, secret) != 0) {
        return jsonrpc_serialize_error(id, SHAPER_RPC_NOT_AUTHORIZED, "secret required", NULL);
    }

    int rc = 0;
    if (op == SHAPER_OP_ANCHOR_LOAD) {
        const cJSON *rk = params ? cJSON_GetObjectItem(params, "rate_kbps") : NULL;
        int rate = cJSON_IsNumber(rk) ? rk->valueint : 0;
        rc = shaper_anchor_apply(rate); /* -1 on a bad rate / failed step */
    } else if (op == SHAPER_OP_ANCHOR_REMOVE) {
        rc = shaper_anchor_clear(); /* fail-OPEN, always 0 */
    } else { /* SHAPER_OP_PACE — honest no-op for now (dummynet shapes in kernel). */
        int did_noop = 0;
        rc = (shaper_execute(op, &did_noop) == SHAPER_OK) ? 0 : -1;
    }
    if (rc != 0) {
        return jsonrpc_serialize_error(id, SHAPER_RPC_CAPABILITY_MISSING, "shaper op failed", NULL);
    }
    return ok_response(id);
}
