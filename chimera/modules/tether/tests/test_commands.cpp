/* Contract for tether.* dispatch (§5 IPC, §6 error codes). RED: commands.cpp
 * returns nullptr for every method, so all cases fail (TEST_ASSERT_NOT_NULL).
 * GREEN builds responses, mutates runtime, dry-runs tether.test, gates pairing
 * (-31004), and rejects unknown (-31002). */
#include "unity.h"

#include <cstdlib>

#include "cJSON.h"

#include "commands.hpp"

using tether::commands_dispatch;
using tether::TetherRuntime;

/* Dispatch + parse; fails the test if dispatch returned NULL (the RED state). */
static cJSON *dispatch_parse(TetherRuntime *rt, const char *method, cJSON *params) {
    cJSON *id = cJSON_CreateNumber(1);
    char *resp = commands_dispatch(rt, method, params, id);
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

static int error_code(cJSON *root) {
    cJSON *err = cJSON_GetObjectItemCaseSensitive(root, "error");
    cJSON *code = cJSON_GetObjectItemCaseSensitive(err, "code");
    return code ? code->valueint : 0;
}

static void test_status_reports_l3_disarmed(void) {
    TetherRuntime rt;
    cJSON *root = dispatch_parse(&rt, "tether.status", nullptr);
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    cJSON *l3 = cJSON_GetObjectItemCaseSensitive(result, "l3_armed");
    TEST_ASSERT_TRUE(cJSON_IsFalse(l3));
    cJSON_Delete(root);
}

static void test_l3_arm_sets_flag(void) {
    TetherRuntime rt;
    cJSON *params = cJSON_CreateObject();
    cJSON_AddStringToObject(params, "confirmation_phrase", "arm it");
    cJSON *root = dispatch_parse(&rt, "tether.l3.arm", params);
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    TEST_ASSERT_TRUE(cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(result, "l3_armed")));
    cJSON_Delete(root);
}

static void test_l3_disarm_clears_flag(void) {
    TetherRuntime rt;
    rt.escalation.l3_armed = true;
    cJSON *root = dispatch_parse(&rt, "tether.l3.disarm", nullptr);
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    TEST_ASSERT_TRUE(cJSON_IsFalse(cJSON_GetObjectItemCaseSensitive(result, "l3_armed")));
    cJSON_Delete(root);
}

/* tether.test is a DRY RUN — returns a report and takes NO real action (§8). */
static void test_dry_run_reports_no_action(void) {
    TetherRuntime rt;
    cJSON *root = dispatch_parse(&rt, "tether.test", nullptr);
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    TEST_ASSERT_NOT_NULL(cJSON_GetObjectItemCaseSensitive(result, "dry_run_report"));
    cJSON_Delete(root);
}

static void test_escalation_cancel(void) {
    TetherRuntime rt;
    cJSON *root = dispatch_parse(&rt, "tether.escalation.cancel", nullptr);
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    TEST_ASSERT_NOT_NULL(result);
    cJSON_Delete(root);
}

static void test_pairing_is_gated(void) {
    TetherRuntime rt;
    cJSON *root = dispatch_parse(&rt, "tether.pair.start", nullptr);
    TEST_ASSERT_EQUAL_INT(TETHER_RPC_PRECONDITION_FAILED, error_code(root));
    cJSON_Delete(root);
}

static void test_unknown_method_31002(void) {
    TetherRuntime rt;
    cJSON *root = dispatch_parse(&rt, "tether.bogus", nullptr);
    TEST_ASSERT_EQUAL_INT(TETHER_RPC_CAPABILITY_MISSING, error_code(root));
    cJSON_Delete(root);
}

/* heighten flips the sensitivity flag and reports a TIGHTER effective grace; the
 * base grace is preserved (proven by relax). */
static void test_heighten_sets_flag(void) {
    TetherRuntime rt;
    cJSON *root = dispatch_parse(&rt, "tether.heighten", nullptr);
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    cJSON *h = cJSON_GetObjectItemCaseSensitive(result, "heightened");
    TEST_ASSERT_TRUE(cJSON_IsTrue(h));
    cJSON *eff = cJSON_GetObjectItemCaseSensitive(result, "effective_grace_ms");
    TEST_ASSERT_TRUE(cJSON_IsNumber(eff));
    TEST_ASSERT_TRUE(eff->valuedouble < static_cast<double>(rt.escalation.grace_ms));
    cJSON_Delete(root);
}

/* relax returns to base sensitivity; the base grace was never overwritten, so the
 * effective grace == base again (idempotent restore). */
static void test_relax_restores_base(void) {
    TetherRuntime rt;
    cJSON *h = dispatch_parse(&rt, "tether.heighten", nullptr);
    cJSON_Delete(h);
    cJSON *root = dispatch_parse(&rt, "tether.relax", nullptr);
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    TEST_ASSERT_TRUE(cJSON_IsFalse(cJSON_GetObjectItemCaseSensitive(result, "heightened")));
    cJSON *eff = cJSON_GetObjectItemCaseSensitive(result, "effective_grace_ms");
    TEST_ASSERT_TRUE(cJSON_IsNumber(eff));
    TEST_ASSERT_EQUAL_INT(static_cast<int>(rt.escalation.grace_ms),
                          static_cast<int>(eff->valuedouble));
    cJSON_Delete(root);
}

/* EMIT-ONLY: heightening brings the ladder sooner, but tether.test stays a DRY
 * RUN — it reports the (tighter) timing and still takes NO action (§8). The change
 * is sensitivity, not actuation. */
static void test_heighten_emit_only(void) {
    TetherRuntime rt;
    cJSON *h = dispatch_parse(&rt, "tether.heighten", nullptr);
    cJSON_Delete(h);
    cJSON *root = dispatch_parse(&rt, "tether.test", nullptr);
    cJSON *result = cJSON_GetObjectItemCaseSensitive(root, "result");
    cJSON *report = cJSON_GetObjectItemCaseSensitive(result, "dry_run_report");
    TEST_ASSERT_NOT_NULL(report);
    TEST_ASSERT_TRUE(cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(report, "dry_run")));
    cJSON *l1 = cJSON_GetObjectItemCaseSensitive(report, "l1_at_ms");
    TEST_ASSERT_TRUE(cJSON_IsNumber(l1));
    TEST_ASSERT_TRUE(l1->valuedouble < static_cast<double>(rt.escalation.grace_ms));
    cJSON_Delete(root);
}

void run_commands_tests(void) {
    RUN_TEST(test_status_reports_l3_disarmed);
    RUN_TEST(test_l3_arm_sets_flag);
    RUN_TEST(test_l3_disarm_clears_flag);
    RUN_TEST(test_dry_run_reports_no_action);
    RUN_TEST(test_escalation_cancel);
    RUN_TEST(test_pairing_is_gated);
    RUN_TEST(test_unknown_method_31002);
    RUN_TEST(test_heighten_sets_flag);
    RUN_TEST(test_relax_restores_base);
    RUN_TEST(test_heighten_emit_only);
}
