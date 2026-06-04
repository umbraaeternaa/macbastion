/* commands — chaff.* JSON-RPC dispatch (§5.1). profile.* deferred (Sub-D6). */
#include "commands.h"

#include <string.h>

#include "generation.h" /* CHAFF_DEFAULT_MULTIPLIER */
#include "jsonrpc.h"

void chaff_runtime_init(chaff_runtime_t *rt) {
    if (!rt) {
        return;
    }
    rt->state = CHAFF_IDLE;
    rt->multiplier = CHAFF_DEFAULT_MULTIPLIER;
    rt->requests_today = 0;
    rt->bytes_today = 0;
}

static char *ok_result(const cJSON *id) {
    cJSON *r = cJSON_CreateObject();
    cJSON_AddBoolToObject(r, "ok", 1);
    return jsonrpc_serialize_response(id, r);
}

char *commands_dispatch(chaff_runtime_t *rt, const endpoint_list_t *eps, const char *method,
                        const cJSON *params, const cJSON *id) {
    if (!method) {
        return NULL;
    }

    if (strcmp(method, "chaff.status") == 0) {
        cJSON *r = cJSON_CreateObject();
        cJSON_AddStringToObject(r, "phase", "generation");
        cJSON_AddBoolToObject(r, "running", rt && rt->state == CHAFF_GENERATING);
        cJSON_AddNumberToObject(r, "requests_today", rt ? (double)rt->requests_today : 0.0);
        cJSON_AddNumberToObject(r, "bytes_today", rt ? (double)rt->bytes_today : 0.0);
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "chaff.generation.start") == 0) {
        if (rt) {
            rt->state = CHAFF_GENERATING;
        }
        return ok_result(id);
    }

    if (strcmp(method, "chaff.generation.stop") == 0) {
        if (rt) {
            rt->state = CHAFF_IDLE;
        }
        return ok_result(id);
    }

    if (strcmp(method, "chaff.config.set") == 0) {
        cJSON *m = cJSON_GetObjectItemCaseSensitive(params, "multiplier");
        if (rt && cJSON_IsNumber(m)) {
            rt->multiplier = m->valuedouble;
        }
        cJSON *r = cJSON_CreateObject();
        cJSON_AddNumberToObject(r, "multiplier", rt ? rt->multiplier : 0.0);
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "chaff.endpoints.list") == 0) {
        cJSON *r = cJSON_CreateObject();
        cJSON *arr = cJSON_CreateArray();
        if (eps) {
            for (size_t i = 0; i < eps->count; i++) {
                cJSON *e = cJSON_CreateObject();
                cJSON_AddStringToObject(e, "url", eps->items[i].url);
                cJSON_AddStringToObject(e, "category", eps->items[i].category);
                cJSON_AddItemToArray(arr, e);
            }
        }
        cJSON_AddItemToObject(r, "endpoints", arr);
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "chaff.endpoints.add") == 0) {
        return ok_result(id);
    }

    if (strcmp(method, "chaff.profile.start") == 0 ||
        strcmp(method, "chaff.profile.stop") == 0) {
        cJSON *data = cJSON_CreateObject();
        cJSON_AddStringToObject(data, "required_capability", "privileged_shim");
        cJSON_AddStringToObject(data, "spec", "\xc2\xa7""7.10/\xc2\xa7""8.8");
        return jsonrpc_serialize_error(id, CHAFF_RPC_PRECONDITION_FAILED,
                                       "profile commands require privileged shim (not yet built)",
                                       data);
    }

    return jsonrpc_serialize_error(id, -32601, "method not found", NULL);
}
