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
#include <time.h>
#include <unistd.h>

#include <sodium.h>

#include "crypto.h"
#include "jsonrpc.h"
#include "keychain.h"
#include "mount.h"
#include "parser.h"

#define VAULT_RELOCK_SECONDS 900   /* auto-relock 15 min after unlock (§5.6 default) */
#define VAULT_MAX_FILE (64 * 1024) /* VD-5: per-file content cap (vaults hold small secrets) */

static cJSON *load_array_file(const char *path); /* fwd: used by unlock (open) + add_file */

/* Unlock context provider (VD-4a). Default reads the clock; module signals are unknown (a
 * not-running module fails closed unless the policy opts in). Tests inject a fixed context. */
static void default_context(VaultContext *out) {
    time_t now = time(NULL);
    struct tm tmv;
    localtime_r(&now, &tmv);
    out->hour = tmv.tm_hour;
    out->weekday = (VaultWeekday)((tmv.tm_wday + 6) % 7); /* tm_wday 0=Sun -> VWD_MON=0 */
    out->day_of_month = tmv.tm_mday;
    out->seconds_since_boot = 0; /* VD-4a: real sysctl kern.boottime gathering deferred */
    out->pulse_mode = VPULSE_UNKNOWN;
    out->tether = VTETHER_UNKNOWN;
    out->network_ssid = NULL;
    out->oracle_score = 0.0;
    out->oracle_known = false;
}

void vault_runtime_tick(vault_runtime_t *rt, long now) {
    if (rt != NULL && rt->relock_at != 0 && now >= rt->relock_at) {
        rt->open_vault_id[0] = '\0';
        rt->relock_at = 0;
    }
}

static vault_context_fn g_context = default_context;

vault_context_fn vault_set_context_provider(vault_context_fn fn) {
    vault_context_fn prev = g_context;
    g_context = fn ? fn : default_context;
    return prev;
}

void vault_runtime_init(vault_runtime_t *rt) {
    if (rt == NULL) {
        return;
    }
    vault_crypto_init(); /* idempotent sodium_init — needed for the unlock derive (VD-4b) */
    rt->open_vault_id[0] = '\0';
    rt->relock_at = 0;
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

/* Find a vault's policy_dsl in the registry by id; copies into out. 1 if found, else 0. */
static int find_policy(const char *meta_dir, const char *vault_id, char *out, size_t outsz) {
    cJSON *reg = load_registry(meta_dir);
    int found = 0;
    const cJSON *e = NULL;
    cJSON_ArrayForEach(e, reg) {
        const cJSON *vid = cJSON_GetObjectItem(e, "vault_id");
        const cJSON *dsl = cJSON_GetObjectItem(e, "policy_dsl");
        if (cJSON_IsString(vid) && strcmp(vid->valuestring, vault_id) == 0 && cJSON_IsString(dsl)) {
            snprintf(out, outsz, "%s", dsl->valuestring);
            found = 1;
            break;
        }
    }
    cJSON_Delete(reg);
    return found;
}

static char *denied(const cJSON *id, const char *reason) {
    cJSON *r = cJSON_CreateObject();
    cJSON_AddStringToObject(r, "denied", reason);
    return jsonrpc_serialize_response(id, r);
}

static void hex_decode16(const char *hex, uint8_t out[16]) {
    for (int i = 0; i < 16; i++) {
        char b[3] = {hex[i * 2], hex[i * 2 + 1], '\0'};
        out[i] = (uint8_t)strtol(b, NULL, 16);
    }
}

/* Derive the vault's key (VD-4b): keychain master secret + BLAKE2b(policy_dsl) + salt(vault_id
 * bytes) -> Argon2id. 0 on success (key filled; caller zeroes), -1 if the keychain or KDF fails.
 * The key materialises ONLY here, on an ALLOW — it is the state-gated secret. */
static int vault_derive_key(const char *vault_id, const char *policy_dsl,
                            uint8_t key[VAULT_KEY_BYTES]) {
    unsigned char master[VAULT_MASTER_SECRET_LEN];
    if (vault_keychain_load_or_create(vault_id, master) != 0) {
        return -1;
    }
    uint8_t policy_hash[32];
    crypto_generichash(policy_hash, sizeof(policy_hash), (const unsigned char *)policy_dsl,
                       strlen(policy_dsl), NULL, 0);
    uint8_t salt[VAULT_SALT_BYTES];
    hex_decode16(vault_id, salt); /* vault_id = 32 hex chars = 16 bytes; stable per vault */
    int rc = vault_crypto_derive(master, sizeof(master), policy_hash, salt, key) ? 0 : -1;
    sodium_memzero(master, sizeof(master));
    return rc;
}

static int hex_decode(const char *hex, unsigned char *out, size_t max) {
    size_t hlen = strlen(hex);
    if (hlen % 2 != 0 || hlen / 2 > max) {
        return -1;
    }
    for (size_t i = 0; i < hlen / 2; i++) {
        char b[3] = {hex[i * 2], hex[i * 2 + 1], '\0'};
        char *end = NULL;
        long v = strtol(b, &end, 16);
        if (end != b + 2) {
            return -1;
        }
        out[i] = (unsigned char)v;
    }
    return (int)(hlen / 2);
}

/* Open every sealed file in `sealed` with `key` (verifying the Poly1305 tag) and materialise the
 * decrypted plaintext into the vault's mount (VD-9a). 1 if ALL open + land in the mount (sets
 * *count); 0 if any entry is malformed, fails to verify (tamper / wrong key), or can't be written
 * to the mount. The plaintext is zeroed from this buffer once handed to the mount. */
static int vault_open_all(const cJSON *sealed, const uint8_t key[VAULT_KEY_BYTES],
                          const char *vault_id, int *count) {
    int n = 0;
    const cJSON *e = NULL;
    cJSON_ArrayForEach(e, sealed) {
        const cJSON *nm = cJSON_GetObjectItem(e, "name");
        const cJSON *nh = cJSON_GetObjectItem(e, "nonce");
        const cJSON *ch = cJSON_GetObjectItem(e, "ct");
        if (!cJSON_IsString(nh) || !cJSON_IsString(ch)) {
            return 0;
        }
        uint8_t nonce[VAULT_NONCE_BYTES];
        if (hex_decode(nh->valuestring, nonce, sizeof(nonce)) != (int)VAULT_NONCE_BYTES) {
            return 0;
        }
        size_t ctlen = strlen(ch->valuestring) / 2;
        if (ctlen < VAULT_TAG_BYTES) {
            return 0;
        }
        unsigned char *ct = malloc(ctlen);
        size_t ptcap = ctlen - VAULT_TAG_BYTES + 1;
        unsigned char *pt = malloc(ptcap);
        int ok = 0;
        if (ct != NULL && pt != NULL && hex_decode(ch->valuestring, ct, ctlen) == (int)ctlen) {
            size_t ptlen = 0;
            if (vault_crypto_open(key, nonce, ct, ctlen, pt, &ptlen)) {
                const char *fname = cJSON_IsString(nm) ? nm->valuestring : "file";
                ok = (vault_mount_put(vault_id, fname, pt, ptlen) == 0) ? 1 : 0;
            }
            sodium_memzero(pt, ptcap);
        }
        free(ct);
        free(pt);
        if (!ok) {
            return 0;
        }
        n++;
    }
    *count = n;
    return 1;
}

/* VD-4a decision + VD-4b key derivation + VD-6 decrypt. ALLOW derives the gated key and OPENS
 * the vault's sealed files (proving the key decrypts the vault), marks it open, returns
 * {ok, files}; keychain/KDF failure -> {denied:key_unavailable}; a file that won't verify ->
 * {denied:integrity}. DEFER -> {defer}; DENY / unknown / another-open -> {denied: reason}. */
static char *handle_unlock(vault_runtime_t *rt, const cJSON *params, const cJSON *id) {
    const cJSON *vid = params ? cJSON_GetObjectItem(params, "vault_id") : NULL;
    if (!cJSON_IsString(vid) || vid->valuestring[0] == '\0') {
        return jsonrpc_serialize_error(id, -32602, "vault_id required", NULL);
    }
    /* Only ONE vault open at a time (§5.6 — bounded memory-dump blast radius). */
    if (rt->open_vault_id[0] != '\0' && strcmp(rt->open_vault_id, vid->valuestring) != 0) {
        return denied(id, "another_vault_open");
    }
    char policy[4096];
    if (!find_policy(rt->meta_dir, vid->valuestring, policy, sizeof(policy))) {
        return denied(id, "no_such_vault");
    }
    VaultContext ctx;
    g_context(&ctx);
    VaultDecision d = vault_policy_decide(policy, &ctx);
    if (d.verdict == VAULT_ALLOW) {
        uint8_t key[VAULT_KEY_BYTES];
        if (vault_derive_key(vid->valuestring, policy, key) != 0) {
            return denied(id, "key_unavailable");
        }
        /* VD-9a: open a RAM-backed mount, then OPEN the sealed files with the gated key and
         * materialise the decrypted plaintext into the mount — it never touches the disk and
         * vanishes on lock. A bad tag (tamper / wrong key) or a failed mount tears it back down. */
        char mountpath[512];
        if (vault_mount_begin(vid->valuestring, mountpath, sizeof(mountpath)) != 0) {
            sodium_memzero(key, sizeof(key));
            return denied(id, "mount_failed");
        }
        char fpath[1200];
        snprintf(fpath, sizeof(fpath), "%s/%s.files.json", rt->meta_dir, vid->valuestring);
        cJSON *sealed = load_array_file(fpath);
        int files = 0;
        int integrity_ok = vault_open_all(sealed, key, vid->valuestring, &files);
        cJSON_Delete(sealed);
        sodium_memzero(key, sizeof(key));
        if (!integrity_ok) {
            vault_mount_end(vid->valuestring); /* don't leave a half-populated mount behind */
            return denied(id, "integrity"); /* a sealed file failed to verify (tamper / wrong key) */
        }
        snprintf(rt->open_vault_id, sizeof(rt->open_vault_id), "%s", vid->valuestring);
        rt->relock_at = (long)time(NULL) + VAULT_RELOCK_SECONDS; /* arm auto-relock (VD-4c) */
        cJSON *r = cJSON_CreateObject();
        cJSON_AddBoolToObject(r, "ok", 1);
        cJSON_AddStringToObject(r, "vault_id", vid->valuestring);
        cJSON_AddNumberToObject(r, "files", files);
        cJSON_AddStringToObject(r, "mount", mountpath);
        return jsonrpc_serialize_response(id, r);
    }
    if (d.verdict == VAULT_DEFER) {
        cJSON *r = cJSON_CreateObject();
        cJSON_AddNumberToObject(r, "defer", (double)d.defer_seconds);
        return jsonrpc_serialize_response(id, r);
    }
    return denied(id, "policy");
}

/* vault.lock (VD-4c): clear the open vault + its relock timer. {ok:true} if it locked the open
 * vault (or the matching one); {ok:false, reason:not_open} if nothing matching is open. */
static char *handle_lock(vault_runtime_t *rt, const cJSON *params, const cJSON *id) {
    const cJSON *vid = params ? cJSON_GetObjectItem(params, "vault_id") : NULL;
    const char *want = cJSON_IsString(vid) ? vid->valuestring : NULL;
    cJSON *r = cJSON_CreateObject();
    if (rt->open_vault_id[0] != '\0' && (want == NULL || strcmp(rt->open_vault_id, want) == 0)) {
        rt->open_vault_id[0] = '\0';
        rt->relock_at = 0;
        cJSON_AddBoolToObject(r, "ok", 1);
    } else {
        cJSON_AddBoolToObject(r, "ok", 0);
        cJSON_AddStringToObject(r, "reason", "not_open");
    }
    return jsonrpc_serialize_response(id, r);
}

static char *hex_encode(const unsigned char *b, size_t n) {
    static const char hexd[] = "0123456789abcdef";
    char *out = malloc(n * 2 + 1);
    if (out == NULL) {
        return NULL;
    }
    for (size_t i = 0; i < n; i++) {
        out[i * 2] = hexd[(b[i] >> 4) & 0x0f];
        out[i * 2 + 1] = hexd[b[i] & 0x0f];
    }
    out[n * 2] = '\0';
    return out;
}

static cJSON *load_array_file(const char *path) {
    FILE *f = fopen(path, "r");
    if (f == NULL) {
        return cJSON_CreateArray();
    }
    char *buf = malloc(8u << 20); /* 8 MiB — holds the sealed-file index */
    if (buf == NULL) {
        fclose(f);
        return cJSON_CreateArray();
    }
    size_t n = fread(buf, 1, (8u << 20) - 1, f);
    fclose(f);
    buf[n] = '\0';
    cJSON *arr = cJSON_Parse(buf);
    free(buf);
    if (!cJSON_IsArray(arr)) {
        cJSON_Delete(arr);
        return cJSON_CreateArray();
    }
    return arr;
}

static int save_array_file(const char *meta_dir, const char *path, const cJSON *arr) {
    if (mkdir_p(meta_dir) != 0) {
        return -1;
    }
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

/* vault.add_file (VD-5): seal a source file into the OPEN vault. Re-derives the vault key,
 * XChaCha20-Poly1305-seals the content, and appends {name, nonce, ct} (hex) to the vault's
 * sealed-file index <meta_dir>/<vault_id>.files.json. Requires the vault to be unlocked. */
static char *handle_add_file(vault_runtime_t *rt, const cJSON *params, const cJSON *id) {
    const cJSON *vid = params ? cJSON_GetObjectItem(params, "vault_id") : NULL;
    const cJSON *src = params ? cJSON_GetObjectItem(params, "source_path") : NULL;
    if (!cJSON_IsString(vid) || !cJSON_IsString(src)) {
        return jsonrpc_serialize_error(id, -32602, "vault_id and source_path required", NULL);
    }
    if (strcmp(rt->open_vault_id, vid->valuestring) != 0) {
        return jsonrpc_serialize_error(id, -31004, "vault not open", NULL);
    }
    char policy[4096];
    if (!find_policy(rt->meta_dir, vid->valuestring, policy, sizeof(policy))) {
        return jsonrpc_serialize_error(id, -32602, "no such vault", NULL);
    }
    FILE *sf = fopen(src->valuestring, "rb");
    if (sf == NULL) {
        return jsonrpc_serialize_error(id, -32602, "cannot read source_path", NULL);
    }
    unsigned char *plain = malloc(VAULT_MAX_FILE);
    if (plain == NULL) {
        fclose(sf);
        return jsonrpc_serialize_error(id, -32000, "out of memory", NULL);
    }
    size_t plen = fread(plain, 1, VAULT_MAX_FILE, sf);
    fclose(sf);

    uint8_t key[VAULT_KEY_BYTES];
    if (vault_derive_key(vid->valuestring, policy, key) != 0) {
        sodium_memzero(plain, VAULT_MAX_FILE);
        free(plain);
        return jsonrpc_serialize_error(id, -31004, "key unavailable", NULL);
    }
    uint8_t nonce[VAULT_NONCE_BYTES];
    unsigned char *ct = malloc(plen + VAULT_TAG_BYTES);
    size_t ct_len = 0;
    int sealed = (ct != NULL) && vault_crypto_seal(key, plain, plen, nonce, ct, &ct_len);
    sodium_memzero(key, sizeof(key));
    sodium_memzero(plain, VAULT_MAX_FILE);
    free(plain);
    if (!sealed) {
        free(ct);
        return jsonrpc_serialize_error(id, -32000, "seal failed", NULL);
    }

    char *nonce_hex = hex_encode(nonce, VAULT_NONCE_BYTES);
    char *ct_hex = hex_encode(ct, ct_len);
    free(ct);
    if (nonce_hex == NULL || ct_hex == NULL) {
        free(nonce_hex);
        free(ct_hex);
        return jsonrpc_serialize_error(id, -32000, "out of memory", NULL);
    }
    char fpath[1200];
    snprintf(fpath, sizeof(fpath), "%s/%s.files.json", rt->meta_dir, vid->valuestring);
    cJSON *files = load_array_file(fpath);
    cJSON *entry = cJSON_CreateObject();
    cJSON_AddStringToObject(entry, "name", src->valuestring);
    cJSON_AddStringToObject(entry, "nonce", nonce_hex);
    cJSON_AddStringToObject(entry, "ct", ct_hex);
    cJSON_AddItemToArray(files, entry);
    int rc = save_array_file(rt->meta_dir, fpath, files);
    cJSON_Delete(files);
    free(nonce_hex);
    free(ct_hex);
    if (rc != 0) {
        return jsonrpc_serialize_error(id, -32000, "persist failed", NULL);
    }
    cJSON *r = cJSON_CreateObject();
    cJSON_AddBoolToObject(r, "ok", 1);
    cJSON_AddStringToObject(r, "name", src->valuestring);
    return jsonrpc_serialize_response(id, r);
}

/* vault.delete (VD-7): permanently remove a vault — drop it from the registry, evict its
 * Keychain master secret (KEK), wipe its sealed-file index, and close it if it is the open
 * vault. {ok:true} on success; an unknown id -> {ok:false, reason:no_such_vault}. */
static char *handle_delete(vault_runtime_t *rt, const cJSON *params, const cJSON *id) {
    const cJSON *vid = cJSON_GetObjectItem(params, "vault_id");
    if (!cJSON_IsString(vid)) {
        return jsonrpc_serialize_error(id, -32602, "vault_id required", NULL);
    }
    cJSON *reg = load_registry(rt->meta_dir);
    int found = -1;
    int n = cJSON_GetArraySize(reg);
    for (int i = 0; i < n; i++) {
        const cJSON *e = cJSON_GetArrayItem(reg, i);
        const cJSON *eid = cJSON_GetObjectItem(e, "vault_id");
        if (cJSON_IsString(eid) && strcmp(eid->valuestring, vid->valuestring) == 0) {
            found = i;
            break;
        }
    }
    if (found < 0) {
        cJSON_Delete(reg);
        cJSON *r = cJSON_CreateObject();
        cJSON_AddBoolToObject(r, "ok", 0);
        cJSON_AddStringToObject(r, "reason", "no_such_vault");
        return jsonrpc_serialize_response(id, r);
    }
    cJSON_DeleteItemFromArray(reg, found);
    int rc = save_registry(rt->meta_dir, reg);
    cJSON_Delete(reg);
    if (rc != 0) {
        return jsonrpc_serialize_error(id, -32000, "persist failed", NULL);
    }
    /* evict the KEK + wipe the sealed-file index (best-effort — the registry drop already
     * makes the vault unreachable; these remove the leftover secret + ciphertext). */
    vault_keychain_delete(vid->valuestring);
    char fpath[1200];
    snprintf(fpath, sizeof(fpath), "%s/%s.files.json", rt->meta_dir, vid->valuestring);
    unlink(fpath);
    /* if the deleted vault was the open one, close it */
    if (strcmp(rt->open_vault_id, vid->valuestring) == 0) {
        rt->open_vault_id[0] = '\0';
        rt->relock_at = 0;
    }
    cJSON *r = cJSON_CreateObject();
    cJSON_AddBoolToObject(r, "ok", 1);
    return jsonrpc_serialize_response(id, r);
}

/* vault.policy.update (VD-8): replace a vault's access policy. Validates the new DSL (fail-closed),
 * then — because the key derives from master||policy_hash — REFUSES a vault that holds sealed
 * content (changing the policy changes the key, which would orphan the ciphertext; MANIFESTO §4:
 * no silent data loss). An empty vault's policy is rewritten in place + the vault closed if open.
 * {ok:true}; {ok:false, reason:no_such_vault|vault_not_empty}; -32602 on an unparsable DSL. */
static char *handle_policy_update(vault_runtime_t *rt, const cJSON *params, const cJSON *id) {
    const cJSON *vid = cJSON_GetObjectItem(params, "vault_id");
    const cJSON *dsl = cJSON_GetObjectItem(params, "policy_dsl");
    if (!cJSON_IsString(vid) || !cJSON_IsString(dsl)) {
        return jsonrpc_serialize_error(id, -32602, "vault_id and policy_dsl required", NULL);
    }
    char errbuf[256];
    VaultPolicy *pol = vault_parse(dsl->valuestring, errbuf, sizeof(errbuf));
    if (pol == NULL) {
        return jsonrpc_serialize_error(id, -32602, "invalid policy_dsl", NULL);
    }
    vault_policy_free(pol);

    cJSON *reg = load_registry(rt->meta_dir);
    cJSON *entry = NULL;
    cJSON *e = NULL;
    cJSON_ArrayForEach(e, reg) {
        const cJSON *eid = cJSON_GetObjectItem(e, "vault_id");
        if (cJSON_IsString(eid) && strcmp(eid->valuestring, vid->valuestring) == 0) {
            entry = e;
            break;
        }
    }
    if (entry == NULL) {
        cJSON_Delete(reg);
        cJSON *r = cJSON_CreateObject();
        cJSON_AddBoolToObject(r, "ok", 0);
        cJSON_AddStringToObject(r, "reason", "no_such_vault");
        return jsonrpc_serialize_response(id, r);
    }
    /* refuse if the vault holds sealed content — re-keying it would orphan the ciphertext */
    char fpath[1200];
    snprintf(fpath, sizeof(fpath), "%s/%s.files.json", rt->meta_dir, vid->valuestring);
    cJSON *sealed = load_array_file(fpath);
    int has_content = cJSON_GetArraySize(sealed) > 0;
    cJSON_Delete(sealed);
    if (has_content) {
        cJSON_Delete(reg);
        cJSON *r = cJSON_CreateObject();
        cJSON_AddBoolToObject(r, "ok", 0);
        cJSON_AddStringToObject(r, "reason", "vault_not_empty");
        return jsonrpc_serialize_response(id, r);
    }
    cJSON_ReplaceItemInObject(entry, "policy_dsl", cJSON_CreateString(dsl->valuestring));
    int rc = save_registry(rt->meta_dir, reg);
    cJSON_Delete(reg);
    if (rc != 0) {
        return jsonrpc_serialize_error(id, -32000, "persist failed", NULL);
    }
    /* the policy (and thus the derived key) changed — close the vault so the next unlock
     * re-evaluates from scratch under the new policy. */
    if (strcmp(rt->open_vault_id, vid->valuestring) == 0) {
        rt->open_vault_id[0] = '\0';
        rt->relock_at = 0;
    }
    cJSON *r = cJSON_CreateObject();
    cJSON_AddBoolToObject(r, "ok", 1);
    return jsonrpc_serialize_response(id, r);
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
    if (strcmp(method, "vault.unlock") == 0) {
        return handle_unlock(rt, params, id);
    }
    if (strcmp(method, "vault.lock") == 0) {
        return handle_lock(rt, params, id);
    }
    if (strcmp(method, "vault.add_file") == 0) {
        return handle_add_file(rt, params, id);
    }
    if (strcmp(method, "vault.delete") == 0) {
        return handle_delete(rt, params, id);
    }
    if (strcmp(method, "vault.policy.update") == 0) {
        return handle_policy_update(rt, params, id);
    }
    return jsonrpc_serialize_error(id, -32601, "method not found", NULL);
}
