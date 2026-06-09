/* GREEN contract for PURGE's purge.* command dispatch (PD-2/PD-3) — the 12 asserts are
 * unchanged from RED. Pins: runtime defaults, status, config.get/set, target add/list/remove, the
 * dry-run test (destroys NOTHING), arm/disarm, and — critically — purge.trigger is GATED
 * (-31004): the dispatch never destroys. */
#include <stdlib.h>

#include "unity.h"

#include "cJSON.h"
#include "commands.h"

static cJSON *do_dispatch(purge_runtime_t *rt, const char *method, cJSON *params) {
    cJSON *id = cJSON_CreateNumber(1);
    char *resp = purge_commands_dispatch(rt, method, params, id);
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

static int int_field(const cJSON *o, const char *k) {
    const cJSON *it = cJSON_GetObjectItem(o, k);
    TEST_ASSERT_NOT_NULL(it);
    return it->valueint;
}

static const char *str_field(const cJSON *o, const char *k) {
    const cJSON *it = cJSON_GetObjectItem(o, k);
    TEST_ASSERT_NOT_NULL(it);
    TEST_ASSERT_NOT_NULL(it->valuestring);
    return it->valuestring;
}

static cJSON *obj(const char *k, cJSON *v) {
    cJSON *o = cJSON_CreateObject();
    cJSON_AddItemToObject(o, k, v);
    return o;
}

static void test_init_defaults(void) {
    purge_runtime_t rt;
    rt.config.post_action = PURGE_STAY; /* non-default, to prove init resets it */
    rt.config.marker = 1;
    rt.armed = 1;
    rt.targets.count = 5;
    purge_runtime_init(&rt);
    TEST_ASSERT_EQUAL_INT(PURGE_REBOOT, rt.config.post_action);
    TEST_ASSERT_EQUAL_INT(0, rt.config.marker);
    TEST_ASSERT_EQUAL_INT(0, rt.armed);
    TEST_ASSERT_EQUAL_INT(0, purge_target_count(&rt.targets));
}

static void test_status(void) {
    purge_runtime_t rt = {0};
    purge_runtime_init(&rt);
    cJSON *root = do_dispatch(&rt, "purge.status", NULL);
    cJSON *res = cJSON_GetObjectItem(root, "result");
    TEST_ASSERT_NOT_NULL(res);
    TEST_ASSERT_EQUAL_INT(0, int_field(res, "armed"));
    TEST_ASSERT_NOT_NULL(cJSON_GetObjectItem(res, "post_action"));
    cJSON_Delete(root);
}

static void test_config_get(void) {
    purge_runtime_t rt = {0};
    purge_runtime_init(&rt);
    cJSON *root = do_dispatch(&rt, "purge.config.get", NULL);
    cJSON *cfg = cJSON_GetObjectItem(cJSON_GetObjectItem(root, "result"), "config");
    TEST_ASSERT_NOT_NULL(cfg);
    TEST_ASSERT_EQUAL_STRING("reboot", str_field(cfg, "post_action"));
    cJSON_Delete(root);
}

static void test_config_set_valid(void) {
    purge_runtime_t rt = {0};
    purge_runtime_init(&rt);
    cJSON *p = cJSON_CreateObject();
    cJSON_AddStringToObject(p, "post_action", "stay");
    cJSON_AddBoolToObject(p, "marker", 1);
    cJSON *root = do_dispatch(&rt, "purge.config.set", p);
    TEST_ASSERT_NOT_NULL(cJSON_GetObjectItem(root, "result"));
    TEST_ASSERT_EQUAL_INT(PURGE_STAY, rt.config.post_action);
    TEST_ASSERT_EQUAL_INT(1, rt.config.marker);
    cJSON_Delete(root);
}

static void test_config_set_invalid(void) {
    purge_runtime_t rt = {0};
    purge_runtime_init(&rt);
    cJSON *root = do_dispatch(&rt, "purge.config.set", obj("post_action", cJSON_CreateString("nuke")));
    cJSON *err = cJSON_GetObjectItem(root, "error");
    TEST_ASSERT_NOT_NULL(err);
    TEST_ASSERT_EQUAL_INT(-32602, int_field(err, "code"));
    TEST_ASSERT_EQUAL_INT(PURGE_REBOOT, rt.config.post_action); /* unchanged */
    cJSON_Delete(root);
}

static void test_target_add_and_list(void) {
    purge_runtime_t rt = {0};
    purge_runtime_init(&rt);
    cJSON *p = cJSON_CreateObject();
    cJSON_AddStringToObject(p, "path", "/vault/x");
    cJSON_AddBoolToObject(p, "encrypted", 1);
    cJSON *root = do_dispatch(&rt, "purge.target.add", p);
    TEST_ASSERT_NOT_NULL(cJSON_GetObjectItem(root, "result"));
    TEST_ASSERT_EQUAL_INT(1, purge_target_count(&rt.targets));
    cJSON_Delete(root);
    cJSON *lroot = do_dispatch(&rt, "purge.target.list", NULL);
    cJSON *tgts = cJSON_GetObjectItem(cJSON_GetObjectItem(lroot, "result"), "targets");
    TEST_ASSERT_TRUE(cJSON_IsArray(tgts));
    TEST_ASSERT_EQUAL_INT(1, cJSON_GetArraySize(tgts));
    cJSON_Delete(lroot);
}

static void test_target_remove(void) {
    purge_runtime_t rt = {0};
    purge_runtime_init(&rt);
    purge_target_add(&rt.targets, "/vault/x", 1);
    cJSON *root = do_dispatch(&rt, "purge.target.remove", obj("path", cJSON_CreateString("/vault/x")));
    TEST_ASSERT_NOT_NULL(cJSON_GetObjectItem(root, "result"));
    TEST_ASSERT_EQUAL_INT(0, purge_target_count(&rt.targets));
    cJSON_Delete(root);
}

static void test_dry_run_destroys_nothing(void) {
    purge_runtime_t rt = {0};
    purge_runtime_init(&rt);
    purge_target_add(&rt.targets, "/enc", 1);
    cJSON *root = do_dispatch(&rt, "purge.test", NULL);
    cJSON *res = cJSON_GetObjectItem(root, "result");
    TEST_ASSERT_NOT_NULL(res);
    TEST_ASSERT_EQUAL_INT(1, int_field(res, "tier0"));
    TEST_ASSERT_NOT_NULL(cJSON_GetObjectItem(res, "tier2_shred"));
    TEST_ASSERT_EQUAL_INT(1, purge_target_count(&rt.targets)); /* dry-run touched nothing */
    cJSON_Delete(root);
}

static void test_arm_disarm(void) {
    purge_runtime_t rt = {0};
    purge_runtime_init(&rt);
    cJSON *root = do_dispatch(&rt, "purge.arm", obj("confirmation_phrase", cJSON_CreateString("yes")));
    TEST_ASSERT_NOT_NULL(cJSON_GetObjectItem(root, "result"));
    TEST_ASSERT_EQUAL_INT(1, rt.armed);
    cJSON_Delete(root);
    cJSON *droot = do_dispatch(&rt, "purge.disarm", NULL);
    TEST_ASSERT_NOT_NULL(cJSON_GetObjectItem(droot, "result"));
    TEST_ASSERT_EQUAL_INT(0, rt.armed);
    cJSON_Delete(droot);
}

static void test_arm_requires_phrase(void) {
    purge_runtime_t rt = {0};
    purge_runtime_init(&rt);
    cJSON *root = do_dispatch(&rt, "purge.arm", NULL);
    TEST_ASSERT_EQUAL_INT(-32602, int_field(cJSON_GetObjectItem(root, "error"), "code"));
    TEST_ASSERT_EQUAL_INT(0, rt.armed);
    cJSON_Delete(root);
}

static void test_trigger_gated(void) {
    purge_runtime_t rt = {0};
    purge_runtime_init(&rt);
    purge_target_add(&rt.targets, "/enc", 1);
    cJSON *root = do_dispatch(&rt, "purge.trigger", obj("authorization", cJSON_CreateString("yes")));
    cJSON *err = cJSON_GetObjectItem(root, "error");
    TEST_ASSERT_NOT_NULL(err);
    TEST_ASSERT_EQUAL_INT(-31004, int_field(err, "code")); /* destruction engine gated */
    TEST_ASSERT_EQUAL_INT(1, purge_target_count(&rt.targets)); /* nothing destroyed */
    cJSON_Delete(root);
}

static void test_unknown_method(void) {
    purge_runtime_t rt = {0};
    purge_runtime_init(&rt);
    cJSON *root = do_dispatch(&rt, "purge.bogus", NULL);
    TEST_ASSERT_EQUAL_INT(-32601, int_field(cJSON_GetObjectItem(root, "error"), "code"));
    cJSON_Delete(root);
}

void run_commands_tests(void) {
    RUN_TEST(test_init_defaults);
    RUN_TEST(test_status);
    RUN_TEST(test_config_get);
    RUN_TEST(test_config_set_valid);
    RUN_TEST(test_config_set_invalid);
    RUN_TEST(test_target_add_and_list);
    RUN_TEST(test_target_remove);
    RUN_TEST(test_dry_run_destroys_nothing);
    RUN_TEST(test_arm_disarm);
    RUN_TEST(test_arm_requires_phrase);
    RUN_TEST(test_trigger_gated);
    RUN_TEST(test_unknown_method);
}
