/* GREEN contract for ECHO's echo.* command dispatch (ED-2/ED-3) — the 8 asserts are
 * unchanged from RED. Pins: runtime defaults, status, config.get/set (valid + invalid), stats
 * (ratio + histogram), start/stop flag, unknown-method error. */
#include <stdlib.h>

#include "unity.h"

#include "cJSON.h"
#include "commands.h"

/* Dispatch + parse the response into a cJSON root (caller frees). params (if non-NULL) is
 * freed here. Asserts a non-NULL response + parse. */
static cJSON *do_dispatch(echo_runtime_t *rt, const char *method, cJSON *params) {
    cJSON *id = cJSON_CreateNumber(1);
    char *resp = echo_commands_dispatch(rt, method, params, id);
    cJSON_Delete(id);
    if (params != NULL) {
        cJSON_Delete(params);
    }
    TEST_ASSERT_NOT_NULL(resp);
    cJSON *root = cJSON_Parse(resp);
    free(resp);
    TEST_ASSERT_NOT_NULL(root);
    return root;
}

static int int_field(const cJSON *obj, const char *key) {
    const cJSON *it = cJSON_GetObjectItem(obj, key);
    TEST_ASSERT_NOT_NULL(it);
    return it->valueint;
}

static void test_runtime_init_defaults(void) {
    echo_runtime_t rt = {0};
    echo_runtime_init(&rt);
    TEST_ASSERT_EQUAL_INT(100, rt.config.target_kbps);
    TEST_ASSERT_EQUAL_INT(200, rt.config.burst_tolerance);
    TEST_ASSERT_EQUAL_INT(0, rt.running);
    TEST_ASSERT_EQUAL_INT(0, (int)rt.stats.ticks);
}

static void test_status(void) {
    echo_runtime_t rt = {0};
    echo_runtime_init(&rt);
    cJSON *root = do_dispatch(&rt, "echo.status", NULL);
    cJSON *res = cJSON_GetObjectItem(root, "result");
    TEST_ASSERT_NOT_NULL(res);
    TEST_ASSERT_NOT_NULL(cJSON_GetObjectItem(res, "running"));
    TEST_ASSERT_EQUAL_INT(100, int_field(res, "target_kbps"));
    cJSON_Delete(root);
}

static void test_config_get(void) {
    echo_runtime_t rt = {0};
    echo_runtime_init(&rt);
    cJSON *root = do_dispatch(&rt, "echo.config.get", NULL);
    cJSON *cfg = cJSON_GetObjectItem(cJSON_GetObjectItem(root, "result"), "config");
    TEST_ASSERT_NOT_NULL(cfg);
    TEST_ASSERT_EQUAL_INT(100, int_field(cfg, "target_kbps"));
    TEST_ASSERT_EQUAL_INT(200, int_field(cfg, "burst_tolerance"));
    cJSON_Delete(root);
}

static void test_config_set_valid(void) {
    echo_runtime_t rt = {0};
    echo_runtime_init(&rt);
    cJSON *params = cJSON_CreateObject();
    cJSON_AddNumberToObject(params, "target_kbps", 500);
    cJSON *root = do_dispatch(&rt, "echo.config.set", params);
    TEST_ASSERT_NOT_NULL(cJSON_GetObjectItem(root, "result"));
    TEST_ASSERT_EQUAL_INT(500, rt.config.target_kbps);
    cJSON_Delete(root);
}

static void test_config_set_invalid(void) {
    echo_runtime_t rt = {0};
    echo_runtime_init(&rt);
    cJSON *params = cJSON_CreateObject();
    cJSON_AddNumberToObject(params, "target_kbps", 0); /* below ECHO_MIN_KBPS */
    cJSON *root = do_dispatch(&rt, "echo.config.set", params);
    cJSON *err = cJSON_GetObjectItem(root, "error");
    TEST_ASSERT_NOT_NULL(err);
    TEST_ASSERT_EQUAL_INT(-32602, int_field(err, "code"));
    TEST_ASSERT_EQUAL_INT(100, rt.config.target_kbps); /* unchanged */
    cJSON_Delete(root);
}

static void test_stats(void) {
    echo_runtime_t rt = {0};
    echo_runtime_init(&rt);
    echo_stats_record(&rt.stats, 0, 1000); /* one idle tick -> 100% padding */
    cJSON *root = do_dispatch(&rt, "echo.stats", NULL);
    cJSON *res = cJSON_GetObjectItem(root, "result");
    TEST_ASSERT_NOT_NULL(res);
    TEST_ASSERT_EQUAL_INT(100, int_field(res, "padding_ratio"));
    cJSON *hist = cJSON_GetObjectItem(res, "histogram");
    TEST_ASSERT_TRUE(cJSON_IsArray(hist));
    TEST_ASSERT_EQUAL_INT(ECHO_HIST_BINS, cJSON_GetArraySize(hist));
    cJSON_Delete(root);
}

static void test_start_stop(void) {
    echo_runtime_t rt = {0};
    echo_runtime_init(&rt);
    cJSON *r1 = do_dispatch(&rt, "echo.start", NULL);
    TEST_ASSERT_EQUAL_INT(1, rt.running);
    cJSON_Delete(r1);
    cJSON *r2 = do_dispatch(&rt, "echo.stop", NULL);
    TEST_ASSERT_EQUAL_INT(0, rt.running);
    cJSON_Delete(r2);
}

static void test_unknown_method(void) {
    echo_runtime_t rt = {0};
    echo_runtime_init(&rt);
    cJSON *root = do_dispatch(&rt, "echo.bogus", NULL);
    cJSON *err = cJSON_GetObjectItem(root, "error");
    TEST_ASSERT_NOT_NULL(err);
    TEST_ASSERT_EQUAL_INT(-32601, int_field(err, "code"));
    cJSON_Delete(root);
}

void run_commands_tests(void) {
    RUN_TEST(test_runtime_init_defaults);
    RUN_TEST(test_status);
    RUN_TEST(test_config_get);
    RUN_TEST(test_config_set_valid);
    RUN_TEST(test_config_set_invalid);
    RUN_TEST(test_stats);
    RUN_TEST(test_start_stop);
    RUN_TEST(test_unknown_method);
}
