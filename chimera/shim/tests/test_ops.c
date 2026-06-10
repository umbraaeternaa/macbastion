/* Contract for the 4-op whitelist (§8.8 enum, SH-5 (c)). RED: ops.c is stubbed,
 * so the method→op mappings and the no-op executor fail. The "unknown" cases
 * pass coincidentally (the stub maps everything to UNKNOWN) — see the RED
 * breakdown in STATE/commit; they become real-pass in GREEN. */
#include "unity.h"

#include "ops.h"
#include "shim.h"

static void test_from_method_lock(void) {
    TEST_ASSERT_EQUAL_INT(SHIM_OP_LOCK, ops_from_method("shim.lock"));
}

static void test_from_method_evict(void) {
    TEST_ASSERT_EQUAL_INT(SHIM_OP_EVICT, ops_from_method("shim.evict"));
}

static void test_from_method_reboot(void) {
    TEST_ASSERT_EQUAL_INT(SHIM_OP_REBOOT, ops_from_method("shim.reboot"));
}

static void test_from_method_killall(void) {
    TEST_ASSERT_EQUAL_INT(SHIM_OP_KILLALL, ops_from_method("shim.killall"));
}

/* Coincidental-pass in RED (stub already returns UNKNOWN); real boundary in GREEN. */
static void test_from_method_unknown(void) {
    TEST_ASSERT_EQUAL_INT(SHIM_OP_UNKNOWN, ops_from_method("shim.bogus"));
}

static void test_from_method_null(void) {
    TEST_ASSERT_EQUAL_INT(SHIM_OP_UNKNOWN, ops_from_method(NULL));
}

static void test_method_name_roundtrip(void) {
    TEST_ASSERT_EQUAL_STRING("shim.lock", ops_method_name(SHIM_OP_LOCK));
    TEST_ASSERT_EQUAL_STRING("shim.evict", ops_method_name(SHIM_OP_EVICT));
    TEST_ASSERT_EQUAL_STRING("shim.reboot", ops_method_name(SHIM_OP_REBOOT));
    TEST_ASSERT_EQUAL_STRING("shim.killall", ops_method_name(SHIM_OP_KILLALL));
}

static void test_method_name_unknown_is_null(void) {
    TEST_ASSERT_NULL(ops_method_name(SHIM_OP_UNKNOWN));
}

/* Slice 3a: LOCK now performs a REAL effect via the injectable lock action — did_noop=0,
 * and the action is invoked. We inject a recording stand-in so no display ever sleeps. */
static int g_mock_lock_calls;
static shim_result_t mock_lock(void) {
    g_mock_lock_calls++;
    return SHIM_OK;
}

static void test_execute_lock_is_real(void) {
    g_mock_lock_calls = 0;
    ops_lock_fn prev = ops_set_lock_action(mock_lock);
    int did_noop = 99;
    TEST_ASSERT_EQUAL_INT(SHIM_OK, ops_execute(SHIM_OP_LOCK, &did_noop));
    TEST_ASSERT_EQUAL_INT(0, did_noop);          /* real effect, not a no-op */
    TEST_ASSERT_EQUAL_INT(1, g_mock_lock_calls); /* the lock action was invoked */
    ops_set_lock_action(prev);
}

/* The destructive ops stay logged no-ops until their own slices (3b+). */
static void test_execute_evict_is_noop(void) {
    int did_noop = 0;
    TEST_ASSERT_EQUAL_INT(SHIM_OK, ops_execute(SHIM_OP_EVICT, &did_noop));
    TEST_ASSERT_EQUAL_INT(1, did_noop);
}

static void test_execute_reboot_is_noop(void) {
    int did_noop = 0;
    TEST_ASSERT_EQUAL_INT(SHIM_OK, ops_execute(SHIM_OP_REBOOT, &did_noop));
    TEST_ASSERT_EQUAL_INT(1, did_noop); /* reboot NEVER real in autotests (SH-11) */
}

static void test_execute_unknown_errors(void) {
    int did_noop = 0;
    TEST_ASSERT_EQUAL_INT(SHIM_ERR_NOTFOUND, ops_execute(SHIM_OP_UNKNOWN, &did_noop));
}

void run_ops_tests(void) {
    RUN_TEST(test_from_method_lock);
    RUN_TEST(test_from_method_evict);
    RUN_TEST(test_from_method_reboot);
    RUN_TEST(test_from_method_killall);
    RUN_TEST(test_from_method_unknown);
    RUN_TEST(test_from_method_null);
    RUN_TEST(test_method_name_roundtrip);
    RUN_TEST(test_method_name_unknown_is_null);
    RUN_TEST(test_execute_lock_is_real);
    RUN_TEST(test_execute_evict_is_noop);
    RUN_TEST(test_execute_reboot_is_noop);
    RUN_TEST(test_execute_unknown_errors);
}
