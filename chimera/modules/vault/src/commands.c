/* VAULT IPC command dispatch — vault.* over JSON-RPC (VD-1). RED: dispatch returns NULL until
 * GREEN (no faked behaviour, MANIFESTO §4). */
#include <stddef.h>
#include <string.h>

#include "commands.h"
#include "jsonrpc.h"

void vault_runtime_init(vault_runtime_t *rt) {
    if (rt != NULL) {
        rt->open_vault_id[0] = '\0';
    }
}

/* The engine methods whose real behaviour (keychain KEK / policy eval / derive / mount) is not
 * built yet — refuse rather than fake it (MANIFESTO §4). */
static int is_engine_method(const char *method) {
    static const char *const ENGINE[] = {
        "vault.create",        "vault.list",     "vault.unlock", "vault.lock",
        "vault.policy.update", "vault.add_file", "vault.delete",
    };
    for (size_t i = 0; i < sizeof(ENGINE) / sizeof(ENGINE[0]); i++) {
        if (strcmp(method, ENGINE[i]) == 0) {
            return 1;
        }
    }
    return 0;
}

char *vault_commands_dispatch(vault_runtime_t *rt, const char *method, const cJSON *params,
                              const cJSON *id) {
    (void)params;
    if (rt == NULL || method == NULL) {
        return NULL;
    }
    if (strcmp(method, "vault.status") == 0) {
        cJSON *r = cJSON_CreateObject();
        cJSON_AddBoolToObject(r, "vault_open", rt->open_vault_id[0] != '\0');
        cJSON_AddStringToObject(r, "open_vault_id", rt->open_vault_id);
        return jsonrpc_serialize_response(id, r);
    }
    if (is_engine_method(method)) {
        return jsonrpc_serialize_error(id, -31004, "vault engine not available", NULL);
    }
    return jsonrpc_serialize_error(id, -32601, "method not found", NULL);
}
