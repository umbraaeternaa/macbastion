/* vault.unlock decision (VD-4a): state-gated — ALLOW only when the policy passes the injected
 * context; DENY otherwise; only one vault open at a time; unknown vault refused. Context is
 * injected (fixed clock); the keychain is the runner's in-memory backend. RED: vault.unlock is
 * gated -31004 until GREEN. */
#include "unity.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "cJSON.h"

#include "commands.h"
#include "keychain.h"

static int g_hour = 12;

static void fixed_ctx(VaultContext *out) {
    out->hour = g_hour;
    out->weekday = VWD_WED;
    out->day_of_month = 15;
    out->seconds_since_boot = 0;
    out->pulse_mode = VPULSE_UNKNOWN;
    out->tether = VTETHER_UNKNOWN;
    out->network_ssid = NULL;
    out->oracle_score = 0.0;
    out->oracle_known = false;
}

static void unlock_setup(void) {
    static char tmp[256];
    snprintf(tmp, sizeof(tmp), "/tmp/chimera-vault-unlock-XXXXXX");
    char *d = mkdtemp(tmp);
    TEST_ASSERT_NOT_NULL(d);
    setenv("CHIMERA_STATE_DIR", d, 1);
    vault_set_context_provider(fixed_ctx);
}

static char *create_vault(vault_runtime_t *rt, const char *name, const char *dsl) {
    cJSON *p = cJSON_CreateObject();
    cJSON_AddStringToObject(p, "name", name);
    cJSON_AddStringToObject(p, "policy_dsl", dsl);
    cJSON *id = cJSON_CreateNumber(1);
    char *resp = vault_commands_dispatch(rt, "vault.create", p, id);
    cJSON_Delete(p);
    cJSON_Delete(id);
    TEST_ASSERT_NOT_NULL(resp);
    cJSON *root = cJSON_Parse(resp);
    free(resp);
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    cJSON *vid = cJSON_GetObjectItemCaseSensitive(result, "vault_id");
    TEST_ASSERT_TRUE(cJSON_IsString(vid));
    char *out = strdup(vid->valuestring);
    cJSON_Delete(root);
    return out;
}

static cJSON *unlock(vault_runtime_t *rt, const char *vault_id) {
    cJSON *p = cJSON_CreateObject();
    cJSON_AddStringToObject(p, "vault_id", vault_id);
    cJSON *id = cJSON_CreateNumber(2);
    char *resp = vault_commands_dispatch(rt, "vault.unlock", p, id);
    cJSON_Delete(p);
    cJSON_Delete(id);
    TEST_ASSERT_NOT_NULL(resp);
    cJSON *root = cJSON_Parse(resp);
    free(resp);
    TEST_ASSERT_NOT_NULL(root);
    return root;
}

static const char *denied_reason(cJSON *root) {
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    cJSON *denied = cJSON_GetObjectItemCaseSensitive(result, "denied");
    return cJSON_IsString(denied) ? denied->valuestring : NULL;
}

static void test_unlock_allows_in_window(void) {
    unlock_setup();
    g_hour = 12;
    vault_runtime_t rt;
    vault_runtime_init(&rt);
    char *vid = create_vault(&rt, "secrets", "allow_when: hour >= 9 and hour <= 17");
    cJSON *root = unlock(&rt, vid);
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    TEST_ASSERT_TRUE(cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(result, "ok")));
    cJSON_Delete(root);
    free(vid);
}

static void test_unlock_denies_fail_closed(void) {
    /* A policy that needs a module signal that is UNKNOWN here -> fail-closed DENY (not a
     * time-projectable DEFER). */
    unlock_setup();
    vault_runtime_t rt;
    vault_runtime_init(&rt);
    char *vid = create_vault(&rt, "secrets", "allow_when: tether == present");
    cJSON *root = unlock(&rt, vid);
    TEST_ASSERT_NOT_NULL(denied_reason(root)); /* a denial reason is present */
    cJSON_Delete(root);
    free(vid);
}

static void test_unlock_another_open_refused(void) {
    unlock_setup();
    g_hour = 12;
    vault_runtime_t rt;
    vault_runtime_init(&rt);
    char *a = create_vault(&rt, "a", "allow_when: hour >= 9 and hour <= 17");
    char *b = create_vault(&rt, "b", "allow_when: hour >= 9 and hour <= 17");
    cJSON_Delete(unlock(&rt, a)); /* opens a */
    cJSON *root = unlock(&rt, b); /* b must be refused while a is open */
    const char *r = denied_reason(root);
    TEST_ASSERT_NOT_NULL(r);
    TEST_ASSERT_EQUAL_STRING("another_vault_open", r);
    cJSON_Delete(root);
    free(a);
    free(b);
}

static int fail_load(const char *v, unsigned char *o) {
    (void)v;
    (void)o;
    return -1;
}
static int fail_store(const char *v, const unsigned char *s) {
    (void)v;
    (void)s;
    return -1;
}

static void test_unlock_key_unavailable_denied(void) {
    /* VD-4b: on ALLOW the key must DERIVE from the keychain KEK; if the keychain is unreachable,
     * unlock is denied (key_unavailable) rather than opening keyless. */
    unlock_setup();
    g_hour = 12;
    vault_runtime_t rt;
    vault_runtime_init(&rt);
    char *vid = create_vault(&rt, "secrets", "allow_when: hour >= 9 and hour <= 17");
    vault_keychain_backend_t fb = {fail_load, fail_store, NULL};
    vault_keychain_set_backend(fb); /* keychain now fails -> derive must fail */
    cJSON *root = unlock(&rt, vid);
    const char *r = denied_reason(root);
    TEST_ASSERT_NOT_NULL(r);
    TEST_ASSERT_EQUAL_STRING("key_unavailable", r);
    cJSON_Delete(root);
    free(vid);
}

static void test_unlock_unknown_vault_denied(void) {
    unlock_setup();
    vault_runtime_t rt;
    vault_runtime_init(&rt);
    cJSON *root = unlock(&rt, "deadbeefdeadbeefdeadbeefdeadbeef");
    const char *r = denied_reason(root);
    TEST_ASSERT_NOT_NULL(r);
    TEST_ASSERT_EQUAL_STRING("no_such_vault", r);
    cJSON_Delete(root);
}

static cJSON *lock_vault(vault_runtime_t *rt, const char *vault_id) {
    cJSON *p = cJSON_CreateObject();
    cJSON_AddStringToObject(p, "vault_id", vault_id);
    cJSON *id = cJSON_CreateNumber(3);
    char *resp = vault_commands_dispatch(rt, "vault.lock", p, id);
    cJSON_Delete(p);
    cJSON_Delete(id);
    TEST_ASSERT_NOT_NULL(resp);
    cJSON *root = cJSON_Parse(resp);
    free(resp);
    TEST_ASSERT_NOT_NULL(root);
    return root;
}

static void test_lock_clears_open(void) {
    unlock_setup();
    g_hour = 12;
    vault_runtime_t rt;
    vault_runtime_init(&rt);
    char *vid = create_vault(&rt, "s", "allow_when: hour >= 9 and hour <= 17");
    cJSON_Delete(unlock(&rt, vid));
    TEST_ASSERT_NOT_EQUAL(0, rt.open_vault_id[0]); /* opened */
    cJSON *root = lock_vault(&rt, vid);
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    TEST_ASSERT_TRUE(cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(result, "ok")));
    cJSON_Delete(root);
    TEST_ASSERT_EQUAL_INT(0, rt.open_vault_id[0]); /* lock cleared the open state */
    free(vid);
}

static void test_relock_when_due(void) {
    unlock_setup();
    g_hour = 12;
    vault_runtime_t rt;
    vault_runtime_init(&rt);
    char *vid = create_vault(&rt, "s", "allow_when: hour >= 9 and hour <= 17");
    cJSON_Delete(unlock(&rt, vid));
    TEST_ASSERT_NOT_EQUAL(0, rt.relock_at); /* unlock armed the relock timer */
    long deadline = rt.relock_at;
    vault_runtime_tick(&rt, deadline - 1);
    TEST_ASSERT_NOT_EQUAL(0, rt.open_vault_id[0]); /* still open before the deadline */
    vault_runtime_tick(&rt, deadline);
    TEST_ASSERT_EQUAL_INT(0, rt.open_vault_id[0]); /* auto-relocked at the deadline */
    free(vid);
}

static cJSON *add_file(vault_runtime_t *rt, const char *vault_id, const char *source_path) {
    cJSON *p = cJSON_CreateObject();
    cJSON_AddStringToObject(p, "vault_id", vault_id);
    cJSON_AddStringToObject(p, "source_path", source_path);
    cJSON *id = cJSON_CreateNumber(4);
    char *resp = vault_commands_dispatch(rt, "vault.add_file", p, id);
    cJSON_Delete(p);
    cJSON_Delete(id);
    TEST_ASSERT_NOT_NULL(resp);
    cJSON *root = cJSON_Parse(resp);
    free(resp);
    TEST_ASSERT_NOT_NULL(root);
    return root;
}

static void test_add_file_seals_when_open(void) {
    unlock_setup();
    g_hour = 12;
    vault_runtime_t rt;
    vault_runtime_init(&rt);
    char *vid = create_vault(&rt, "s", "allow_when: hour >= 9 and hour <= 17");
    cJSON_Delete(unlock(&rt, vid)); /* open */
    char src[256];
    snprintf(src, sizeof(src), "/tmp/chimera-vault-src-XXXXXX");
    int fd = mkstemp(src);
    TEST_ASSERT_TRUE(fd >= 0);
    TEST_ASSERT_EQUAL_INT(14, (int)write(fd, "secret-content", 14));
    close(fd);
    cJSON *root = add_file(&rt, vid, src);
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    TEST_ASSERT_TRUE(cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(result, "ok")));
    cJSON_Delete(root);
    unlink(src);
    free(vid);
}

static void test_add_file_refused_when_locked(void) {
    unlock_setup();
    vault_runtime_t rt;
    vault_runtime_init(&rt);
    char *vid = create_vault(&rt, "s", "allow_when: hour >= 9 and hour <= 17"); /* NOT unlocked */
    cJSON *root = add_file(&rt, vid, "/tmp/does-not-matter");
    TEST_ASSERT_NOT_NULL(cJSON_GetObjectItemCaseSensitive(root, "error")); /* refused: vault locked */
    cJSON_Delete(root);
    free(vid);
}

static void test_unlock_opens_sealed_files(void) {
    /* End-to-end crypto round-trip: add_file seals content; a later unlock derives the same key
     * and OPENS it (tag verifies) -> {ok, files:1}. Proves the state-gated key decrypts the vault. */
    unlock_setup();
    g_hour = 12;
    vault_runtime_t rt;
    vault_runtime_init(&rt);
    char *vid = create_vault(&rt, "s", "allow_when: hour >= 9 and hour <= 17");
    cJSON_Delete(unlock(&rt, vid)); /* open (empty) */
    char src[256];
    snprintf(src, sizeof(src), "/tmp/chimera-vault-rt-XXXXXX");
    int fd = mkstemp(src);
    TEST_ASSERT_TRUE(fd >= 0);
    TEST_ASSERT_EQUAL_INT(18, (int)write(fd, "round-trip-content", 18));
    close(fd);
    cJSON_Delete(add_file(&rt, vid, src));
    unlink(src);
    cJSON_Delete(lock_vault(&rt, vid)); /* close */
    cJSON *root = unlock(&rt, vid);     /* reopen -> opens the sealed file */
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    TEST_ASSERT_TRUE(cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(result, "ok")));
    cJSON *files = cJSON_GetObjectItemCaseSensitive(result, "files");
    TEST_ASSERT_TRUE(cJSON_IsNumber(files));
    TEST_ASSERT_EQUAL_INT(1, files->valueint); /* the sealed file decrypted */
    cJSON_Delete(root);
    free(vid);
}

static cJSON *policy_update(vault_runtime_t *rt, const char *vault_id, const char *dsl) {
    cJSON *p = cJSON_CreateObject();
    cJSON_AddStringToObject(p, "vault_id", vault_id);
    cJSON_AddStringToObject(p, "policy_dsl", dsl);
    cJSON *id = cJSON_CreateNumber(9);
    char *resp = vault_commands_dispatch(rt, "vault.policy.update", p, id);
    cJSON_Delete(p);
    cJSON_Delete(id);
    TEST_ASSERT_NOT_NULL(resp);
    cJSON *root = cJSON_Parse(resp);
    free(resp);
    TEST_ASSERT_NOT_NULL(root);
    return root;
}

static void test_policy_update_refused_with_content(void) {
    /* Changing the policy changes the derived key, which would orphan sealed ciphertext —
     * policy.update must refuse a non-empty vault (MANIFESTO §4: no silent data loss). */
    unlock_setup();
    g_hour = 12;
    vault_runtime_t rt;
    vault_runtime_init(&rt);
    char *vid = create_vault(&rt, "s", "allow_when: hour >= 9 and hour <= 17");
    cJSON_Delete(unlock(&rt, vid)); /* open */
    char src[256];
    snprintf(src, sizeof(src), "/tmp/chimera-vault-pu-XXXXXX");
    int fd = mkstemp(src);
    TEST_ASSERT_TRUE(fd >= 0);
    TEST_ASSERT_EQUAL_INT(6, (int)write(fd, "secret", 6));
    close(fd);
    cJSON_Delete(add_file(&rt, vid, src));
    unlink(src);
    cJSON_Delete(lock_vault(&rt, vid));
    cJSON *root = policy_update(&rt, vid, "allow_when: hour >= 0 and hour <= 23");
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    TEST_ASSERT_TRUE(cJSON_IsFalse(cJSON_GetObjectItemCaseSensitive(result, "ok")));
    TEST_ASSERT_EQUAL_STRING(
        "vault_not_empty",
        cJSON_GetObjectItemCaseSensitive(result, "reason")->valuestring);
    cJSON_Delete(root);
    free(vid);
}

static void test_policy_update_changes_decision(void) {
    /* create with an ALLOW-now policy, re-policy to a fail-closed DENY, then unlock must be
     * denied — proving the policy was genuinely rewritten in the registry. */
    unlock_setup();
    g_hour = 12;
    vault_runtime_t rt;
    vault_runtime_init(&rt);
    char *vid = create_vault(&rt, "s", "allow_when: hour >= 9 and hour <= 17");
    cJSON *uroot = policy_update(&rt, vid, "allow_when: tether == present");
    TEST_ASSERT_TRUE(cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(
        cJSON_GetObjectItemCaseSensitive(uroot, "result"), "ok")));
    cJSON_Delete(uroot);
    cJSON *root = unlock(&rt, vid); /* now evaluated under the NEW policy -> denied */
    TEST_ASSERT_NOT_NULL(denied_reason(root));
    cJSON_Delete(root);
    free(vid);
}

void run_unlock_tests(void) {
    RUN_TEST(test_unlock_allows_in_window);
    RUN_TEST(test_unlock_denies_fail_closed);
    RUN_TEST(test_unlock_another_open_refused);
    RUN_TEST(test_unlock_key_unavailable_denied);
    RUN_TEST(test_unlock_unknown_vault_denied);
    RUN_TEST(test_lock_clears_open);
    RUN_TEST(test_relock_when_due);
    RUN_TEST(test_add_file_seals_when_open);
    RUN_TEST(test_add_file_refused_when_locked);
    RUN_TEST(test_unlock_opens_sealed_files);
    RUN_TEST(test_policy_update_refused_with_content);
    RUN_TEST(test_policy_update_changes_decision);
}
