/* VAULT command-dispatch contract (VD-1): vault.status is real; the engine methods are gated
 * -31004 (not built); unknown -> -32601. RED: vault_commands_dispatch returns NULL until GREEN. */
#include "unity.h"

#include <stdlib.h>

#include "cJSON.h"

#include "commands.h"

static cJSON *dispatch(const char *method) {
    vault_runtime_t rt;
    vault_runtime_init(&rt);
    cJSON *id = cJSON_CreateNumber(1);
    char *resp = vault_commands_dispatch(&rt, method, NULL, id);
    cJSON_Delete(id);
    TEST_ASSERT_NOT_NULL(resp);
    cJSON *root = cJSON_Parse(resp);
    free(resp);
    TEST_ASSERT_NOT_NULL(root);
    return root;
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

static void test_unlock_is_gated_31004(void) {
    cJSON *root = dispatch("vault.unlock");
    TEST_ASSERT_EQUAL_INT(-31004, error_code(root));
    cJSON_Delete(root);
}

static void test_create_is_gated_31004(void) {
    cJSON *root = dispatch("vault.create");
    TEST_ASSERT_EQUAL_INT(-31004, error_code(root));
    cJSON_Delete(root);
}

static void test_unknown_method_is_32601(void) {
    cJSON *root = dispatch("vault.bogus");
    TEST_ASSERT_EQUAL_INT(-32601, error_code(root));
    cJSON_Delete(root);
}

void run_commands_tests(void) {
    RUN_TEST(test_status_reports_no_open_vault);
    RUN_TEST(test_unlock_is_gated_31004);
    RUN_TEST(test_create_is_gated_31004);
    RUN_TEST(test_unknown_method_is_32601);
}
