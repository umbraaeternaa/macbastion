/* ECHO IPC command dispatch — echo.* methods over JSON-RPC (§5 IPC API, ED-2/ED-3).
 * Builds responses from the config + stats cores; the socket loop is a later slice. */
#include <stddef.h>
#include <string.h>

#include "commands.h"
#include "jsonrpc.h"

void echo_runtime_init(echo_runtime_t *rt) {
    if (rt == NULL) {
        return;
    }
    rt->config = echo_config_default();
    echo_stats_init(&rt->stats);
    rt->running = 0;
}

static cJSON *config_obj(const echo_config_t *cfg) {
    cJSON *c = cJSON_CreateObject();
    cJSON_AddNumberToObject(c, "target_kbps", cfg->target_kbps);
    cJSON_AddNumberToObject(c, "burst_tolerance", cfg->burst_tolerance);
    return c;
}

char *echo_commands_dispatch(echo_runtime_t *rt, const char *method, const cJSON *params,
                             const cJSON *id) {
    if (rt == NULL || method == NULL) {
        return NULL;
    }

    if (strcmp(method, "echo.status") == 0) {
        cJSON *r = cJSON_CreateObject();
        cJSON_AddBoolToObject(r, "running", rt->running);
        cJSON_AddNumberToObject(r, "target_kbps", rt->config.target_kbps);
        cJSON_AddNumberToObject(r, "padding_ratio", echo_padding_ratio_pct(&rt->stats));
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "echo.config.get") == 0) {
        cJSON *r = cJSON_CreateObject();
        cJSON_AddItemToObject(r, "config", config_obj(&rt->config));
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "echo.config.set") == 0) {
        const cJSON *tk = params ? cJSON_GetObjectItem(params, "target_kbps") : NULL;
        const cJSON *bt = params ? cJSON_GetObjectItem(params, "burst_tolerance") : NULL;
        const int *tp = NULL;
        const int *bp = NULL;
        int tval;
        int bval;
        if (cJSON_IsNumber(tk)) {
            tval = tk->valueint;
            tp = &tval;
        }
        if (cJSON_IsNumber(bt)) {
            bval = bt->valueint;
            bp = &bval;
        }
        if (echo_config_set(&rt->config, tp, bp) != 0) {
            return jsonrpc_serialize_error(id, -32602, "invalid config", NULL);
        }
        cJSON *r = cJSON_CreateObject();
        cJSON_AddItemToObject(r, "config", config_obj(&rt->config));
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "echo.stats") == 0) {
        cJSON *r = cJSON_CreateObject();
        cJSON_AddNumberToObject(r, "padding_ratio", echo_padding_ratio_pct(&rt->stats));
        cJSON *hist = cJSON_CreateArray();
        for (int i = 0; i < ECHO_HIST_BINS; i++) {
            cJSON_AddItemToArray(hist, cJSON_CreateNumber((double)rt->stats.hist[i]));
        }
        cJSON_AddItemToObject(r, "histogram", hist);
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "echo.start") == 0 || strcmp(method, "echo.stop") == 0) {
        rt->running = (strcmp(method, "echo.start") == 0) ? 1 : 0;
        cJSON *r = cJSON_CreateObject();
        cJSON_AddBoolToObject(r, "running", rt->running);
        return jsonrpc_serialize_response(id, r);
    }

    return jsonrpc_serialize_error(id, -32601, "method not found", NULL);
}
