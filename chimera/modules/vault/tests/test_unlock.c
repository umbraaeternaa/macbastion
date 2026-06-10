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

void run_unlock_tests(void) {
    RUN_TEST(test_unlock_allows_in_window);
    RUN_TEST(test_unlock_denies_fail_closed);
    RUN_TEST(test_unlock_another_open_refused);
    RUN_TEST(test_unlock_unknown_vault_denied);
}
