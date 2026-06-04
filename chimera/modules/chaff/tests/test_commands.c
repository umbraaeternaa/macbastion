/* RED-B contract for chaff.* dispatch + profile.* DEFER (Sub-D6). Fails until GREEN. */
#include "unity.h"

#include <stdlib.h>

#include "commands.h"
#include "generation.h" /* CHAFF_DEFAULT_MULTIPLIER */

static endpoint_t C_ITEMS[] = {
    {(char *)"https://a.com", (char *)"news"},
    {(char *)"https://b.com", (char *)"dev"},
};
static const endpoint_list_t C_LIST = {C_ITEMS, 2};

static void test_runtime_init_defaults(void) {
    chaff_runtime_t rt = {0};
    chaff_runtime_init(&rt);
    TEST_ASSERT_EQUAL_DOUBLE(CHAFF_DEFAULT_MULTIPLIER, rt.multiplier);
    TEST_ASSERT_EQUAL_INT(CHAFF_IDLE, rt.state);
}

static void test_status_dispatch(void) {
    chaff_runtime_t rt = {0};
    chaff_runtime_init(&rt);
    cJSON *id = cJSON_CreateNumber(1);
    char *resp = commands_dispatch(&rt, &C_LIST, "chaff.status", NULL, id);
    TEST_ASSERT_NOT_NULL(resp);
    cJSON_Delete(id);
    free(resp);
}

static void test_generation_start_dispatch(void) {
    chaff_runtime_t rt = {0};
    chaff_runtime_init(&rt);
    cJSON *id = cJSON_CreateNumber(2);
    char *resp = commands_dispatch(&rt, &C_LIST, "chaff.generation.start", NULL, id);
    TEST_ASSERT_NOT_NULL(resp);
    TEST_ASSERT_EQUAL_INT(CHAFF_GENERATING, rt.state);
    cJSON_Delete(id);
    free(resp);
}

static void test_config_set_multiplier(void) {
    chaff_runtime_t rt = {0};
    chaff_runtime_init(&rt);
    cJSON *id = cJSON_CreateNumber(3);
    cJSON *params = cJSON_CreateObject();
    cJSON_AddNumberToObject(params, "multiplier", 7.0);
    char *resp = commands_dispatch(&rt, &C_LIST, "chaff.config.set", params, id);
    TEST_ASSERT_NOT_NULL(resp);
    TEST_ASSERT_EQUAL_DOUBLE(7.0, rt.multiplier);
    cJSON_Delete(params);
    cJSON_Delete(id);
    free(resp);
}

static void test_endpoints_list_dispatch(void) {
    chaff_runtime_t rt = {0};
    chaff_runtime_init(&rt);
    cJSON *id = cJSON_CreateNumber(4);
    char *resp = commands_dispatch(&rt, &C_LIST, "chaff.endpoints.list", NULL, id);
    TEST_ASSERT_NOT_NULL(resp);
    cJSON_Delete(id);
    free(resp);
}

static void test_profile_start_deferred(void) {
    chaff_runtime_t rt = {0};
    chaff_runtime_init(&rt);
    cJSON *id = cJSON_CreateNumber(5);
    char *resp = commands_dispatch(&rt, &C_LIST, "chaff.profile.start", NULL, id);
    TEST_ASSERT_NOT_NULL(resp);
    cJSON *parsed = cJSON_Parse(resp);
    TEST_ASSERT_NOT_NULL(parsed);
    cJSON *err = cJSON_GetObjectItem(parsed, "error");
    TEST_ASSERT_NOT_NULL(err);
    cJSON *code = cJSON_GetObjectItem(err, "code");
    TEST_ASSERT_NOT_NULL(code);
    TEST_ASSERT_EQUAL_INT(CHAFF_RPC_PRECONDITION_FAILED, code->valueint);
    cJSON_Delete(parsed);
    cJSON_Delete(id);
    free(resp);
}

void run_commands_tests(void) {
    RUN_TEST(test_runtime_init_defaults);
    RUN_TEST(test_status_dispatch);
    RUN_TEST(test_generation_start_dispatch);
    RUN_TEST(test_config_set_multiplier);
    RUN_TEST(test_endpoints_list_dispatch);
    RUN_TEST(test_profile_start_deferred);
}
