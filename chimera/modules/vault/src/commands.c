/* VAULT IPC command dispatch — vault.* over JSON-RPC.
 *   VD-1: vault.status (real); the unlock engine gated -31004 (no faked behaviour, MANIFESTO §4).
 *   VD-2: vault.create / vault.list — a small registry persisted to <state_dir>/vault/registry.json
 *         (the same state Tier-0 wipes). policy_dsl is validated through the real parser.
 * Still gated: unlock / lock / policy.update / add_file / delete (keychain KEK + mount slices). */
#include "commands.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include "jsonrpc.h"
#include "keychain.h"
#include "parser.h"

void vault_runtime_init(vault_runtime_t *rt) {
    if (rt == NULL) {
        return;
    }
    rt->open_vault_id[0] = '\0';
    const char *sd = getenv("CHIMERA_STATE_DIR");
    if (sd != NULL && sd[0] != '\0') {
        snprintf(rt->meta_dir, sizeof(rt->meta_dir), "%s/vault", sd);
    } else {
        const char *home = getenv("HOME");
        snprintf(rt->meta_dir, sizeof(rt->meta_dir), "%s/.config/chimera/state/vault",
                 home ? home : ".");
    }
}

static void gen_vault_id(char out[33]) {
    unsigned char raw[16];
    arc4random_buf(raw, sizeof(raw));
    static const char hexd[] = "0123456789abcdef";
    for (int i = 0; i < 16; i++) {
        out[i * 2] = hexd[(raw[i] >> 4) & 0x0f];
        out[i * 2 + 1] = hexd[raw[i] & 0x0f];
    }
    out[32] = '\0';
}

/* mkdir -p: create each path component, ignoring EEXIST. 0 iff the dir exists afterwards. */
static int mkdir_p(const char *dir) {
    char tmp[1024];
    snprintf(tmp, sizeof(tmp), "%s", dir);
    for (char *p = tmp + 1; *p != '\0'; p++) {
        if (*p == '/') {
            *p = '\0';
            mkdir(tmp, 0700);
            *p = '/';
        }
    }
    mkdir(tmp, 0700);
    struct stat st;
    return (stat(tmp, &st) == 0 && S_ISDIR(st.st_mode)) ? 0 : -1;
}

/* The vault registry array (or a fresh empty array if absent/corrupt). Caller deletes. */
static cJSON *load_registry(const char *meta_dir) {
    char path[1100];
    snprintf(path, sizeof(path), "%s/registry.json", meta_dir);
    FILE *f = fopen(path, "r");
    if (f == NULL) {
        return cJSON_CreateArray();
    }
    char buf[65536];
    size_t n = fread(buf, 1, sizeof(buf) - 1, f);
    fclose(f);
    buf[n] = '\0';
    cJSON *arr = cJSON_Parse(buf);
    if (!cJSON_IsArray(arr)) {
        cJSON_Delete(arr);
        return cJSON_CreateArray();
    }
    return arr;
}

static int save_registry(const char *meta_dir, const cJSON *arr) {
    if (mkdir_p(meta_dir) != 0) {
        return -1;
    }
    char path[1100];
    snprintf(path, sizeof(path), "%s/registry.json", meta_dir);
    char *s = cJSON_PrintUnformatted(arr);
    if (s == NULL) {
        return -1;
    }
    FILE *f = fopen(path, "w");
    if (f == NULL) {
        free(s);
        return -1;
    }
    size_t len = strlen(s);
    size_t wrote = fwrite(s, 1, len, f);
    fclose(f);
    free(s);
    return (wrote == len) ? 0 : -1;
}

static char *handle_create(vault_runtime_t *rt, const cJSON *params, const cJSON *id) {
    const cJSON *name = params ? cJSON_GetObjectItem(params, "name") : NULL;
    const cJSON *dsl = params ? cJSON_GetObjectItem(params, "policy_dsl") : NULL;
    if (!cJSON_IsString(name) || name->valuestring[0] == '\0') {
        return jsonrpc_serialize_error(id, -32602, "name required", NULL);
    }
    if (!cJSON_IsString(dsl)) {
        return jsonrpc_serialize_error(id, -32602, "policy_dsl required", NULL);
    }
    char errbuf[256];
    VaultPolicy *pol = vault_parse(dsl->valuestring, errbuf, sizeof(errbuf));
    if (pol == NULL) {
        return jsonrpc_serialize_error(id, -32602, "invalid policy_dsl", NULL);
    }
    vault_policy_free(pol);

    char vid[33];
    gen_vault_id(vid);

    /* Provision the per-vault master secret in the Keychain (VD-3) — the KEK the unlock engine
     * will derive from + the item the privileged shim's evict (PURGE Tier-0) destroys. */
    unsigned char master[VAULT_MASTER_SECRET_LEN];
    if (vault_keychain_load_or_create(vid, master) != 0) {
        return jsonrpc_serialize_error(id, -32000, "keychain unavailable", NULL);
    }
    memset(master, 0, sizeof(master)); /* not needed past provisioning; derive happens at unlock */

    cJSON *reg = load_registry(rt->meta_dir);
    cJSON *entry = cJSON_CreateObject();
    cJSON_AddStringToObject(entry, "vault_id", vid);
    cJSON_AddStringToObject(entry, "name", name->valuestring);
    cJSON_AddStringToObject(entry, "policy_dsl", dsl->valuestring);
    cJSON_AddItemToArray(reg, entry);
    int rc = save_registry(rt->meta_dir, reg);
    cJSON_Delete(reg);
    if (rc != 0) {
        return jsonrpc_serialize_error(id, -32000, "persist failed", NULL);
    }
    cJSON *r = cJSON_CreateObject();
    cJSON_AddStringToObject(r, "vault_id", vid);
    return jsonrpc_serialize_response(id, r);
}

static char *handle_list(vault_runtime_t *rt, const cJSON *id) {
    cJSON *reg = load_registry(rt->meta_dir);
    cJSON *out = cJSON_CreateArray();
    const cJSON *e = NULL;
    cJSON_ArrayForEach(e, reg) {
        const cJSON *vid = cJSON_GetObjectItem(e, "vault_id");
        const cJSON *nm = cJSON_GetObjectItem(e, "name");
        cJSON *o = cJSON_CreateObject();
        cJSON_AddStringToObject(o, "vault_id", cJSON_IsString(vid) ? vid->valuestring : "");
        cJSON_AddStringToObject(o, "name", cJSON_IsString(nm) ? nm->valuestring : "");
        cJSON_AddItemToArray(out, o);
    }
    cJSON_Delete(reg);
    cJSON *r = cJSON_CreateObject();
    cJSON_AddItemToObject(r, "vaults", out);
    return jsonrpc_serialize_response(id, r);
}

/* The methods whose real behaviour (keychain KEK / policy eval / derive / mount) is not built
 * yet — refuse rather than fake it (MANIFESTO §4). */
static int is_engine_method(const char *method) {
    static const char *const ENGINE[] = {
        "vault.unlock", "vault.lock", "vault.policy.update", "vault.add_file", "vault.delete",
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
    if (rt == NULL || method == NULL) {
        return NULL;
    }
    if (strcmp(method, "vault.status") == 0) {
        cJSON *r = cJSON_CreateObject();
        cJSON_AddBoolToObject(r, "vault_open", rt->open_vault_id[0] != '\0');
        cJSON_AddStringToObject(r, "open_vault_id", rt->open_vault_id);
        return jsonrpc_serialize_response(id, r);
    }
    if (strcmp(method, "vault.create") == 0) {
        return handle_create(rt, params, id);
    }
    if (strcmp(method, "vault.list") == 0) {
        return handle_list(rt, id);
    }
    if (is_engine_method(method)) {
        return jsonrpc_serialize_error(id, -31004, "vault engine not available", NULL);
    }
    return jsonrpc_serialize_error(id, -32601, "method not found", NULL);
}
