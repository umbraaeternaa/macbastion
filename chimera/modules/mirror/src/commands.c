/* commands — mirror.* JSON-RPC dispatch (§5.4 §5). status, profile.set, the
 * exclude add/remove/list ops, stats and disable operate on the in-memory
 * runtime; enable is GATED (-31004) until code-signing + Accessibility TCC exist
 * (§6/§9, Sub-M1). */
#include "commands.h"

#include <ApplicationServices/ApplicationServices.h>
#include <string.h>
#include <time.h>

#include "jsonrpc.h"

/* Accessibility-permission probe (AX-1). Real default asks the OS via the public TCC
 * API; tests inject a deterministic stub through mirror_set_accessibility_check. */
static int mirror_ax_trusted_real(void) { return AXIsProcessTrusted() ? 1 : 0; }
static int (*g_ax_check)(void) = mirror_ax_trusted_real;

void mirror_set_accessibility_check(int (*fn)(void)) {
    g_ax_check = fn ? fn : mirror_ax_trusted_real;
}

void mirror_runtime_init(mirror_runtime_t *rt) {
    if (!rt) {
        return;
    }
    rt->enabled = 0;
    rt->profile = MIRROR_PROFILE_DEFAULT; /* medium (§3) */
    rt->exclusions.count = 0;
    for (int i = 0; i < MIRROR_EV__COUNT; i++) {
        rt->stats.counts[i] = 0;
    }
    rt->rng_state = (uint64_t)time(NULL) ^ 0x9e3779b97f4a7c15ULL; /* nonzero seed */
    pthread_mutex_init(&rt->mutex, NULL);
    rt->stop = 0;
    rt->evq_head = NULL;
    rt->evq_tail = NULL;
    rt->heartbeat_at = 0;
}

/* {"ok": true} success body. */
static char *ok_result(const cJSON *id) {
    cJSON *r = cJSON_CreateObject();
    cJSON_AddBoolToObject(r, "ok", 1);
    return jsonrpc_serialize_response(id, r);
}

/* {"exclusions": [...]} from the runtime list. */
static char *exclusions_result(const mirror_runtime_t *rt, const cJSON *id) {
    cJSON *r = cJSON_CreateObject();
    cJSON *arr = cJSON_CreateArray();
    if (rt) {
        for (size_t i = 0; i < rt->exclusions.count; i++) {
            cJSON_AddItemToArray(arr, cJSON_CreateString(rt->exclusions.items[i]));
        }
    }
    cJSON_AddItemToObject(r, "exclusions", arr);
    return jsonrpc_serialize_response(id, r);
}

char *commands_dispatch(mirror_runtime_t *rt, const char *method, const cJSON *params,
                        const cJSON *id) {
    if (!method) {
        return NULL;
    }

    if (strcmp(method, "mirror.status") == 0) {
        uint64_t shaped = 0;
        if (rt) {
            for (int i = 0; i < MIRROR_EV__COUNT; i++) {
                shaped += rt->stats.counts[i];
            }
        }
        cJSON *r = cJSON_CreateObject();
        cJSON_AddBoolToObject(r, "enabled", rt && rt->enabled);
        cJSON_AddStringToObject(r, "profile",
                                profile_to_str(rt ? rt->profile : MIRROR_PROFILE_DEFAULT));
        cJSON_AddNumberToObject(r, "events_shaped_today", (double)shaped);
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "mirror.profile.set") == 0) {
        cJSON *p = cJSON_GetObjectItemCaseSensitive(params, "profile");
        if (!rt || !cJSON_IsString(p)) {
            return jsonrpc_serialize_error(id, -32602, "invalid params: profile required", NULL);
        }
        mirror_profile_t prof = profile_from_str(p->valuestring);
        if (prof == (mirror_profile_t)(-1)) {
            return jsonrpc_serialize_error(id, -32602, "invalid params: unknown profile", NULL);
        }
        rt->profile = prof;
        cJSON *r = cJSON_CreateObject();
        cJSON_AddStringToObject(r, "profile", profile_to_str(rt->profile));
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "mirror.exclude.add") == 0 ||
        strcmp(method, "mirror.exclude.remove") == 0) {
        cJSON *b = cJSON_GetObjectItemCaseSensitive(params, "bundle_id");
        if (!rt || !cJSON_IsString(b)) {
            return jsonrpc_serialize_error(id, -32602, "invalid params: bundle_id required", NULL);
        }
        mirror_result_t rc = (method[15] == 'a') /* "mirror.exclude.[a]dd" vs "[r]emove" */
                                 ? exclude_add(&rt->exclusions, b->valuestring)
                                 : exclude_remove(&rt->exclusions, b->valuestring);
        if (rc != MIRROR_OK) {
            return jsonrpc_serialize_error(id, MIRROR_RPC_PRECONDITION_FAILED,
                                           "exclusion list full or entry not found", NULL);
        }
        return exclusions_result(rt, id);
    }

    if (strcmp(method, "mirror.exclude.list") == 0) {
        return exclusions_result(rt, id);
    }

    if (strcmp(method, "mirror.stats") == 0) {
        static const char *const NAMES[MIRROR_EV__COUNT] = {"mouse_move", "mouse_click", "key_down",
                                                            "key_up", "scroll"};
        cJSON *r = cJSON_CreateObject();
        for (int i = 0; i < MIRROR_EV__COUNT; i++) {
            cJSON_AddNumberToObject(r, NAMES[i], rt ? (double)rt->stats.counts[i] : 0.0);
        }
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "mirror.disable") == 0) {
        if (rt) {
            rt->enabled = 0;
        }
        return ok_result(id);
    }

    if (strcmp(method, "mirror.enable") == 0) {
        /* AX-1: consult the REAL Accessibility permission first, so the operator gets an
         * honest, specific next step instead of one blanket "not built" wall. Both states
         * still return -31004 (enable can't proceed yet) — but the REASON is now true. */
        int ax_ok = g_ax_check();
        cJSON *data = cJSON_CreateObject();
        cJSON_AddStringToObject(data, "spec", "\xc2\xa7""6/\xc2\xa7""9");
        cJSON_AddBoolToObject(data, "accessibility_granted", ax_ok);
        if (!ax_ok) {
            cJSON_AddStringToObject(data, "required_capability", "accessibility");
            return jsonrpc_serialize_error(
                id, MIRROR_RPC_PRECONDITION_FAILED,
                "mirror.enable requires Accessibility permission (grant it in System "
                "Settings > Privacy & Security > Accessibility)",
                data);
        }
        /* Accessibility IS granted; the remaining gate is code-signing for the event tap,
         * which is not built yet — the next stage of this arc. */
        cJSON_AddStringToObject(data, "required_capability", "code_signing");
        return jsonrpc_serialize_error(
            id, MIRROR_RPC_PRECONDITION_FAILED,
            "mirror.enable: Accessibility granted; code-signing for the event tap is not "
            "built yet",
            data);
    }

    return jsonrpc_serialize_error(id, -32601, "method not found", NULL);
}
