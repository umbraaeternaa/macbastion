/* RED-B contract for mirror.* dispatch + enable DEFER (Sub-M1). Fails against the
 * no-op runtime_init + NULL dispatch stub until GREEN. */
#include "unity.h"

#include <stdlib.h>

#include "commands.h"

/* Init must set the documented defaults: disabled, profile = medium. Stub is a
 * no-op on the zeroed struct, so profile reads as LIGHT (0) -> FAIL. */
static void test_runtime_init_defaults(void) {
    mirror_runtime_t rt = {0};
    mirror_runtime_init(&rt);
    TEST_ASSERT_EQUAL_INT(0, rt.enabled);
    TEST_ASSERT_EQUAL_INT(MIRROR_PROFILE_MEDIUM, rt.profile);
}

/* status returns a response. Stub returns NULL -> FAIL. */
static void test_status_dispatch(void) {
    mirror_runtime_t rt = {0};
    mirror_runtime_init(&rt);
    cJSON *id = cJSON_CreateNumber(1);
    char *resp = commands_dispatch(&rt, "mirror.status", NULL, id);
    TEST_ASSERT_NOT_NULL(resp);
    cJSON_Delete(id);
    free(resp);
}

/* profile.set updates the runtime profile. Stub no-op -> FAIL. */
static void test_profile_set_dispatch(void) {
    mirror_runtime_t rt = {0};
    mirror_runtime_init(&rt);
    cJSON *id = cJSON_CreateNumber(2);
    cJSON *params = cJSON_CreateObject();
    cJSON_AddStringToObject(params, "profile", "heavy");
    char *resp = commands_dispatch(&rt, "mirror.profile.set", params, id);
    TEST_ASSERT_NOT_NULL(resp);
    TEST_ASSERT_EQUAL_INT(MIRROR_PROFILE_HEAVY, rt.profile);
    cJSON_Delete(params);
    cJSON_Delete(id);
    free(resp);
}

/* exclude.add adds to the runtime list. Stub -> count stays 0 -> FAIL. */
static void test_exclude_add_dispatch(void) {
    mirror_runtime_t rt = {0};
    mirror_runtime_init(&rt);
    cJSON *id = cJSON_CreateNumber(3);
    cJSON *params = cJSON_CreateObject();
    cJSON_AddStringToObject(params, "bundle_id", "com.apple.Terminal");
    char *resp = commands_dispatch(&rt, "mirror.exclude.add", params, id);
    TEST_ASSERT_NOT_NULL(resp);
    TEST_ASSERT_EQUAL_UINT(1, rt.exclusions.count);
    cJSON_Delete(params);
    cJSON_Delete(id);
    free(resp);
}

/* stats returns a response. Stub NULL -> FAIL. */
static void test_stats_dispatch(void) {
    mirror_runtime_t rt = {0};
    mirror_runtime_init(&rt);
    cJSON *id = cJSON_CreateNumber(4);
    char *resp = commands_dispatch(&rt, "mirror.stats", NULL, id);
    TEST_ASSERT_NOT_NULL(resp);
    cJSON_Delete(id);
    free(resp);
}

/* enable is GATED on code-signing + TCC: must return a -31004 error response.
 * Stub returns NULL -> TEST_ASSERT_NOT_NULL fails -> FAIL. */
static void test_enable_deferred(void) {
    mirror_runtime_t rt = {0};
    mirror_runtime_init(&rt);
    cJSON *id = cJSON_CreateNumber(5);
    char *resp = commands_dispatch(&rt, "mirror.enable", NULL, id);
    TEST_ASSERT_NOT_NULL(resp);
    cJSON *parsed = cJSON_Parse(resp);
    TEST_ASSERT_NOT_NULL(parsed);
    cJSON *err = cJSON_GetObjectItem(parsed, "error");
    TEST_ASSERT_NOT_NULL(err);
    cJSON *code = cJSON_GetObjectItem(err, "code");
    TEST_ASSERT_NOT_NULL(code);
    TEST_ASSERT_EQUAL_INT(MIRROR_RPC_PRECONDITION_FAILED, code->valueint);
    cJSON_Delete(parsed);
    cJSON_Delete(id);
    free(resp);
}

void run_commands_tests(void) {
    RUN_TEST(test_runtime_init_defaults);
    RUN_TEST(test_status_dispatch);
    RUN_TEST(test_profile_set_dispatch);
    RUN_TEST(test_exclude_add_dispatch);
    RUN_TEST(test_stats_dispatch);
    RUN_TEST(test_enable_deferred);
}
