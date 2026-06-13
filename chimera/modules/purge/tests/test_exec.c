/* PG-exec: the tier executor runs a plan's enabled tiers in key-first order via the seams.
 * Hermetic — counting stubs replace the no-op tier actions; nothing is destroyed. */
#include <stddef.h>
#include <string.h>

#include "unity.h"

#include "exec.h"
#include "secrets.h"
#include "tests.h"

static int g_t0, g_t1, g_t3;
static int count_t0(void) {
    g_t0++;
    return 0;
}
static int count_t1(void) {
    g_t1++;
    return 0;
}
static int count_t3(void) {
    g_t3++;
    return 0;
}
static int fail_action(void) { return 1; }

static void inject_counting_seams(void) {
    g_t0 = g_t1 = g_t3 = 0;
    purge_set_tier0_action(count_t0);
    purge_set_tier1_action(count_t1);
    purge_set_tier3_action(count_t3);
}

static void reset_seams(void) {
    purge_set_tier0_action(NULL);
    purge_set_tier1_action(NULL);
    purge_set_tier3_action(NULL);
}

/* plan fields: {tier0, tier1, tier2_shred, tier2_skip, tier3}. */

static void test_execute_runs_all_enabled_tiers(void) {
    inject_counting_seams();
    purge_plan_t plan = {1, 1, 3, 0, 1};
    purge_exec_result_t r = purge_execute(&plan);
    TEST_ASSERT_EQUAL_INT(1, r.tier0_done);
    TEST_ASSERT_EQUAL_INT(1, r.tier1_done);
    TEST_ASSERT_EQUAL_INT(3, r.tier2_shred); /* carried from the plan */
    TEST_ASSERT_EQUAL_INT(1, r.tier3_done);
    TEST_ASSERT_EQUAL_INT(1, g_t0);
    TEST_ASSERT_EQUAL_INT(1, g_t1);
    TEST_ASSERT_EQUAL_INT(1, g_t3);
    reset_seams();
}

static void test_execute_skips_disabled_tier1(void) {
    inject_counting_seams();
    purge_plan_t plan = {1, 0, 0, 0, 1}; /* tier1 off */
    purge_exec_result_t r = purge_execute(&plan);
    TEST_ASSERT_EQUAL_INT(1, r.tier0_done);
    TEST_ASSERT_EQUAL_INT(0, r.tier1_done);
    TEST_ASSERT_EQUAL_INT(0, g_t1); /* tier1 action NOT invoked */
    TEST_ASSERT_EQUAL_INT(1, r.tier3_done);
    reset_seams();
}

static void test_execute_records_tier_failure(void) {
    inject_counting_seams();
    purge_set_tier1_action(fail_action); /* tier1 fails */
    purge_plan_t plan = {1, 1, 0, 0, 1};
    purge_exec_result_t r = purge_execute(&plan);
    TEST_ASSERT_EQUAL_INT(0, r.tier1_done); /* failure recorded */
    TEST_ASSERT_EQUAL_INT(1, r.tier0_done); /* other tiers still run */
    TEST_ASSERT_EQUAL_INT(1, r.tier3_done);
    reset_seams();
}

static void test_execute_null_plan_destroys_nothing(void) {
    inject_counting_seams();
    purge_exec_result_t r = purge_execute(NULL);
    TEST_ASSERT_EQUAL_INT(0, r.tier0_done);
    TEST_ASSERT_EQUAL_INT(0, r.tier3_done);
    TEST_ASSERT_EQUAL_INT(0, g_t0); /* no action invoked on a NULL plan */
    reset_seams();
}

/* Integration: with NO injected stub, the executor's REAL default tier3 action zeroes a
 * registered sensitive buffer in RAM — proves the secrets registry is wired into exec. */
static void test_execute_tier3_really_wipes_registered_ram(void) {
    reset_seams();        /* tier3 falls back to its real default (purge_secret_clear_all) */
    purge_secret_reset();
    unsigned char buf[48];
    memset(buf, 0xAA, sizeof buf);
    TEST_ASSERT_EQUAL_INT(0, purge_secret_register(buf, sizeof buf));
    purge_plan_t plan = {0, 0, 0, 0, 1}; /* tier3 only */
    purge_exec_result_t r = purge_execute(&plan);
    TEST_ASSERT_EQUAL_INT(1, r.tier3_done);
    for (size_t i = 0; i < sizeof buf; i++) {
        TEST_ASSERT_EQUAL_UINT8(0x00, buf[i]); /* tier3 zeroed real RAM */
    }
    purge_secret_reset();
}

void run_exec_tests(void) {
    RUN_TEST(test_execute_runs_all_enabled_tiers);
    RUN_TEST(test_execute_skips_disabled_tier1);
    RUN_TEST(test_execute_records_tier_failure);
    RUN_TEST(test_execute_null_plan_destroys_nothing);
    RUN_TEST(test_execute_tier3_really_wipes_registered_ram);
}
