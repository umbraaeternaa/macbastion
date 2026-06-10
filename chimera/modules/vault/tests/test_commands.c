/* VAULT command-dispatch contract (VD-1): vault.status is real; the engine methods are gated
 * -31004 (not built); unknown -> -32601. RED: vault_commands_dispatch returns NULL until GREEN. */
#include "unity.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "cJSON.h"

#include "commands.h"
#include "tests.h"

/* Point CHIMERA_STATE_DIR at a fresh temp dir so create/list never touch the real state. */
static char g_tmp_state[256];
static void setup_tmp_state(void) {
    snprintf(g_tmp_state, sizeof(g_tmp_state), "/tmp/chimera-vault-test-XXXXXX");
    char *d = mkdtemp(g_tmp_state);
    TEST_ASSERT_NOT_NULL(d);
    setenv("CHIMERA_STATE_DIR", d, 1);
}

static cJSON *dispatch_params(const char *method, cJSON *params) {
    vault_runtime_t rt;
    vault_runtime_init(&rt);
    cJSON *id = cJSON_CreateNumber(1);
    char *resp = vault_commands_dispatch(&rt, method, params, id);
    cJSON_Delete(id);
    TEST_ASSERT_NOT_NULL(resp);
    cJSON *root = cJSON_Parse(resp);
    free(resp);
    TEST_ASSERT_NOT_NULL(root);
    return root;
}

static cJSON *dispatch(const char *method) {
    return dispatch_params(method, NULL);
}

static int error_code(cJSON *root) {
    cJSON *err = cJSON_GetObjectItemCaseSensitive(root, "error");
    cJSON *code = cJSON_GetObjectItemCaseSensitive(err, "code");
    return code ? code->valueint : 0;
}

static void test_status_reports_no_open_vault(void) {
    cJSON *root = dispatch("vault.status");
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    TEST_ASSERT_TRUE(cJSON_IsFalse(cJSON_GetObjectItemCaseSensitive(result, "vault_open")));
    cJSON_Delete(root);
}

static void test_add_file_is_gated_31004(void) {
    cJSON *root = dispatch("vault.add_file"); /* content/decrypt engine not built yet (VD-5) */
    TEST_ASSERT_EQUAL_INT(-31004, error_code(root));
    cJSON_Delete(root);
}

static cJSON *make_create_params(const char *name, const char *dsl) {
    cJSON *p = cJSON_CreateObject();
    cJSON_AddStringToObject(p, "name", name);
    cJSON_AddStringToObject(p, "policy_dsl", dsl);
    return p;
}

static void test_create_returns_vault_id(void) {
    setup_tmp_state();
    cJSON *params = make_create_params("secrets", "allow_when: hour >= 9 and hour <= 17");
    cJSON *root = dispatch_params("vault.create", params);
    cJSON_Delete(params);
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    cJSON *vid = cJSON_GetObjectItemCaseSensitive(result, "vault_id");
    TEST_ASSERT_TRUE(cJSON_IsString(vid));
    TEST_ASSERT_EQUAL_INT(32, (int)strlen(vid->valuestring)); /* 16 random bytes, hex */
    cJSON_Delete(root);
}

static void test_create_rejects_bad_policy(void) {
    setup_tmp_state();
    cJSON *params = make_create_params("x", "this is not valid dsl !!!");
    cJSON *root = dispatch_params("vault.create", params);
    cJSON_Delete(params);
    TEST_ASSERT_EQUAL_INT(-32602, error_code(root)); /* fail-closed on an unparsable policy */
    cJSON_Delete(root);
}

static void test_list_returns_created_vault(void) {
    setup_tmp_state();
    cJSON *params = make_create_params("alpha", "allow_when: hour >= 9 and hour <= 17");
    cJSON_Delete(dispatch_params("vault.create", params));
    cJSON_Delete(params);
    cJSON *root = dispatch("vault.list");
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    cJSON *vaults = cJSON_GetObjectItemCaseSensitive(result, "vaults");
    TEST_ASSERT_TRUE(cJSON_IsArray(vaults));
    TEST_ASSERT_EQUAL_INT(1, cJSON_GetArraySize(vaults));
    cJSON *first = cJSON_GetArrayItem(vaults, 0);
    TEST_ASSERT_EQUAL_STRING("alpha", cJSON_GetObjectItem(first, "name")->valuestring);
    cJSON_Delete(root);
}

static void test_create_provisions_keychain_kek(void) {
    setup_tmp_state(); /* setUp already installed a fresh in-memory keychain */
    cJSON *params = make_create_params("kektest", "allow_when: hour >= 9 and hour <= 17");
    cJSON_Delete(dispatch_params("vault.create", params));
    cJSON_Delete(params);
    TEST_ASSERT_EQUAL_INT(1, vault_test_keychain_count()); /* create provisioned exactly one KEK */
}

static void test_unknown_method_is_32601(void) {
    cJSON *root = dispatch("vault.bogus");
    TEST_ASSERT_EQUAL_INT(-32601, error_code(root));
    cJSON_Delete(root);
}

void run_commands_tests(void) {
    RUN_TEST(test_status_reports_no_open_vault);
    RUN_TEST(test_add_file_is_gated_31004);
    RUN_TEST(test_create_returns_vault_id);
    RUN_TEST(test_create_rejects_bad_policy);
    RUN_TEST(test_list_returns_created_vault);
    RUN_TEST(test_create_provisions_keychain_kek);
    RUN_TEST(test_unknown_method_is_32601);
}
