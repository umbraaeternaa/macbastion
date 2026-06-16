/* PURGE IPC command dispatch — purge.* methods over JSON-RPC (§7 IPC API, PD-2/PD-3).
 * Builds responses from the plan + targets + config cores. purge.trigger runs the REAL tier
 * EXECUTOR (exec.c) once armed — tier0 (state files) + tier2 (encrypted operator targets) +
 * tier3 (RAM-wipe) destroy for real; tier1 (VAULT KEK shred) is the one deferred no-op, covered
 * at the operator level by core.purge -> shim.evict. An UNARMED trigger is refused -31004
 * (operator opt-in; no accidental destruction), NOT because the engine is unbuilt. */
#include <stddef.h>
#include <string.h>

#include "commands.h"
#include "exec.h"
#include "jsonrpc.h"

void purge_runtime_init(purge_runtime_t *rt) {
    if (rt == NULL) {
        return;
    }
    purge_targets_init(&rt->targets);
    rt->config = purge_config_default();
    rt->armed = 0;
}

static cJSON *targets_array(const purge_targets_t *t) {
    cJSON *arr = cJSON_CreateArray();
    int n = purge_target_count(t);
    for (int i = 0; i < n; i++) {
        const purge_target_t *tg = purge_target_at(t, i);
        if (tg == NULL) {
            continue;
        }
        cJSON *o = cJSON_CreateObject();
        cJSON_AddStringToObject(o, "path", tg->path);
        cJSON_AddBoolToObject(o, "encrypted", tg->encrypted);
        cJSON_AddItemToArray(arr, o);
    }
    return arr;
}

static char *targets_response(const purge_targets_t *t, const cJSON *id) {
    cJSON *r = cJSON_CreateObject();
    cJSON_AddItemToObject(r, "targets", targets_array(t));
    return jsonrpc_serialize_response(id, r);
}

static cJSON *config_obj(const purge_config_t *c) {
    cJSON *o = cJSON_CreateObject();
    cJSON_AddStringToObject(o, "post_action", purge_post_action_str(c->post_action));
    cJSON_AddBoolToObject(o, "marker", c->marker);
    return o;
}

char *purge_commands_dispatch(purge_runtime_t *rt, const char *method, const cJSON *params,
                              const cJSON *id) {
    if (rt == NULL || method == NULL) {
        return NULL;
    }

    if (strcmp(method, "purge.status") == 0) {
        cJSON *r = cJSON_CreateObject();
        cJSON_AddBoolToObject(r, "armed", rt->armed);
        cJSON_AddStringToObject(r, "post_action", purge_post_action_str(rt->config.post_action));
        cJSON_AddBoolToObject(r, "marker", rt->config.marker);
        cJSON_AddNumberToObject(r, "targets", purge_target_count(&rt->targets));
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "purge.config.get") == 0) {
        cJSON *r = cJSON_CreateObject();
        cJSON_AddItemToObject(r, "config", config_obj(&rt->config));
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "purge.config.set") == 0) {
        const cJSON *pa = params ? cJSON_GetObjectItem(params, "post_action") : NULL;
        const cJSON *mk = params ? cJSON_GetObjectItem(params, "marker") : NULL;
        const char *pa_str = cJSON_IsString(pa) ? pa->valuestring : NULL;
        const int *mp = NULL;
        int mval;
        if (cJSON_IsBool(mk)) {
            mval = cJSON_IsTrue(mk) ? 1 : 0;
            mp = &mval;
        }
        if (purge_config_set(&rt->config, pa_str, mp) != 0) {
            return jsonrpc_serialize_error(id, -32602, "invalid config", NULL);
        }
        cJSON *r = cJSON_CreateObject();
        cJSON_AddItemToObject(r, "config", config_obj(&rt->config));
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "purge.target.add") == 0) {
        const cJSON *path = params ? cJSON_GetObjectItem(params, "path") : NULL;
        const cJSON *enc = params ? cJSON_GetObjectItem(params, "encrypted") : NULL;
        if (!cJSON_IsString(path)) {
            return jsonrpc_serialize_error(id, -32602, "path required", NULL);
        }
        if (purge_target_add(&rt->targets, path->valuestring, cJSON_IsTrue(enc) ? 1 : 0) < 0) {
            return jsonrpc_serialize_error(id, -32602, "target rejected", NULL);
        }
        return targets_response(&rt->targets, id);
    }

    if (strcmp(method, "purge.target.remove") == 0) {
        const cJSON *path = params ? cJSON_GetObjectItem(params, "path") : NULL;
        if (!cJSON_IsString(path)) {
            return jsonrpc_serialize_error(id, -32602, "path required", NULL);
        }
        purge_target_remove(&rt->targets, path->valuestring);
        return targets_response(&rt->targets, id);
    }

    if (strcmp(method, "purge.target.list") == 0) {
        return targets_response(&rt->targets, id);
    }

    if (strcmp(method, "purge.test") == 0) {
        purge_plan_t plan = purge_plan_targets(&rt->targets, 1, 1); /* dry-run: destroys nothing */
        cJSON *r = cJSON_CreateObject();
        cJSON_AddNumberToObject(r, "tier0", plan.tier0);
        cJSON_AddNumberToObject(r, "tier1", plan.tier1);
        cJSON_AddNumberToObject(r, "tier2_shred", plan.tier2_shred);
        cJSON_AddNumberToObject(r, "tier2_skip", plan.tier2_skip);
        cJSON_AddNumberToObject(r, "tier3", plan.tier3);
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "purge.arm") == 0) {
        const cJSON *ph = params ? cJSON_GetObjectItem(params, "confirmation_phrase") : NULL;
        if (!cJSON_IsString(ph) || ph->valuestring[0] == '\0') {
            return jsonrpc_serialize_error(id, -32602, "confirmation_phrase required", NULL);
        }
        rt->armed = 1; /* real authorization is gated; this slice only flips the flag */
        cJSON *r = cJSON_CreateObject();
        cJSON_AddBoolToObject(r, "armed", 1);
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "purge.disarm") == 0) {
        rt->armed = 0;
        cJSON *r = cJSON_CreateObject();
        cJSON_AddBoolToObject(r, "armed", 0);
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "purge.trigger") == 0) {
        /* Authorization gate (§6): must be armed (purge.arm with a confirmation phrase) first.
         * An unarmed trigger is refused — no accidental destruction. */
        if (!rt->armed) {
            return jsonrpc_serialize_error(id, -31004, "purge not armed (call purge.arm first)",
                                           NULL);
        }
        /* Run the REAL executor (exec.c) over the live plan: tier0 unlinks registered state
         * files, tier2 unlinks ENCRYPTED operator targets (unencrypted are refused, §8), tier3
         * zeroes registered RAM secrets; tier1 (VAULT KEK-shred) is the one deferred no-op (§4).
         * The trigger is single-shot: firing disarms, so a re-trigger needs a fresh arm. */
        purge_plan_t plan = purge_plan_targets(&rt->targets, 1, 1);
        purge_exec_result_t res = purge_execute(&plan, &rt->targets);
        rt->armed = 0;
        cJSON *r = cJSON_CreateObject();
        cJSON_AddBoolToObject(r, "fired", 1);
        cJSON_AddNumberToObject(r, "tier0", res.tier0_done);
        cJSON_AddNumberToObject(r, "tier1", res.tier1_done);
        cJSON_AddNumberToObject(r, "tier2_shred", res.tier2_shred);
        cJSON_AddNumberToObject(r, "tier2_skip", res.tier2_skip);
        cJSON_AddNumberToObject(r, "tier3", res.tier3_done);
        return jsonrpc_serialize_response(id, r);
    }

    return jsonrpc_serialize_error(id, -32601, "method not found", NULL);
}
