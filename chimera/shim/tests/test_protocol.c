/* Contract for JSON-RPC dispatch (§6 error codes, shim.* namespace). RED:
 * protocol.c is stubbed (returns NULL), so every case fails. GREEN builds:
 *   shim.ping            -> {"pong": true}
 *   shim.lock (authed)   -> {"ok": true, "noop": true}   (F3 no-op)
 *   any, unauthorized    -> error -31007 (not authorized)
 *   unknown (authed)     -> error -31002 (capability missing) */
#include "unity.h"

#include <stdlib.h>

#include "cJSON.h"

#include "protocol.h"
#include "shim.h"

/* Parse a dispatch response; returns the owned cJSON root (caller deletes) or
 * NULL. Fails the test if the dispatcher returned NULL (the RED state). */
static cJSON *dispatch_parse(const char *method, int authorized) {
    cJSON *id = cJSON_CreateNumber(1);
    char *resp = protocol_dispatch(method, NULL, id, authorized, NULL);
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

static void test_ping_returns_pong(void) {
    cJSON *root = dispatch_parse("shim.ping", 1);
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    cJSON *pong = cJSON_GetObjectItemCaseSensitive(result, "pong");
    TEST_ASSERT_TRUE(cJSON_IsTrue(pong));
    cJSON_Delete(root);
}

static void test_authorized_op_is_noop(void) {
    cJSON *root = dispatch_parse("shim.lock", 1);
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    TEST_ASSERT_TRUE(cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(result, "ok")));
    TEST_ASSERT_TRUE(cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(result, "noop")));
    cJSON_Delete(root);
}

static void test_unauthorized_is_31007(void) {
    cJSON *root = dispatch_parse("shim.lock", 0);
    TEST_ASSERT_EQUAL_INT(SHIM_RPC_NOT_AUTHORIZED, error_code(root));
    cJSON_Delete(root);
}

static void test_unknown_method_is_31002(void) {
    cJSON *root = dispatch_parse("shim.bogus", 1);
    TEST_ASSERT_EQUAL_INT(SHIM_RPC_CAPABILITY_MISSING, error_code(root));
    cJSON_Delete(root);
}

/* Slice 2: destructive ops (evict/reboot/killall) require params.secret == the per-boot
 * secret; lock/ping do not (SS-2 staged). 64 'a'/'b' stand in for hex secrets. */
static const char *SEC_A =
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
static const char *SEC_B =
    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";

static cJSON *dispatch_secret(const char *method, const char *params_secret,
                              const char *shim_secret) {
    cJSON *id = cJSON_CreateNumber(1);
    cJSON *params = NULL;
    if (params_secret) {
        params = cJSON_CreateObject();
        cJSON_AddStringToObject(params, "secret", params_secret);
    }
    char *resp = protocol_dispatch(method, params, id, 1, shim_secret);
    cJSON_Delete(id);
    if (params) {
        cJSON_Delete(params);
    }
    TEST_ASSERT_NOT_NULL(resp);
    cJSON *root = cJSON_Parse(resp);
    free(resp);
    TEST_ASSERT_NOT_NULL(root);
    return root;
}

static void test_destructive_without_secret_is_31007(void) {
    cJSON *root = dispatch_secret("shim.evict", NULL, SEC_A);
    TEST_ASSERT_EQUAL_INT(SHIM_RPC_NOT_AUTHORIZED, error_code(root));
    cJSON_Delete(root);
}

static void test_destructive_with_secret_is_noop(void) {
    cJSON *root = dispatch_secret("shim.evict", SEC_A, SEC_A);
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    TEST_ASSERT_TRUE(cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(result, "ok")));
    cJSON_Delete(root);
}

static void test_destructive_wrong_secret_is_31007(void) {
    cJSON *root = dispatch_secret("shim.evict", SEC_B, SEC_A);
    TEST_ASSERT_EQUAL_INT(SHIM_RPC_NOT_AUTHORIZED, error_code(root));
    cJSON_Delete(root);
}

static void test_lock_needs_no_secret(void) {
    cJSON *root = dispatch_secret("shim.lock", NULL, SEC_A);
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    TEST_ASSERT_TRUE(cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(result, "ok")));
    cJSON_Delete(root);
}

void run_protocol_tests(void) {
    RUN_TEST(test_ping_returns_pong);
    RUN_TEST(test_authorized_op_is_noop);
    RUN_TEST(test_unauthorized_is_31007);
    RUN_TEST(test_unknown_method_is_31002);
    RUN_TEST(test_destructive_without_secret_is_31007);
    RUN_TEST(test_destructive_with_secret_is_noop);
    RUN_TEST(test_destructive_wrong_secret_is_31007);
    RUN_TEST(test_lock_needs_no_secret);
}
