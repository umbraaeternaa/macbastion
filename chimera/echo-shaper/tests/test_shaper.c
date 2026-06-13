/* A1 skeleton: the ECHO packet-shaper op whitelist + FAIL-OPEN no-op executor. Hermetic —
 * pure logic, no pf, no root, nothing touched. */
#include <stddef.h>

#include "unity.h"

#include "shaper.h"
#include "tests.h"

static void test_method_maps_to_op(void) {
    TEST_ASSERT_EQUAL_INT(SHAPER_OP_ANCHOR_LOAD, shaper_op_from_method("shaper.anchor.load"));
    TEST_ASSERT_EQUAL_INT(SHAPER_OP_PACE, shaper_op_from_method("shaper.pace"));
    TEST_ASSERT_EQUAL_INT(SHAPER_OP_ANCHOR_REMOVE, shaper_op_from_method("shaper.anchor.remove"));
}

static void test_unknown_method_is_rejected(void) {
    TEST_ASSERT_EQUAL_INT(SHAPER_OP_UNKNOWN, shaper_op_from_method("shaper.bogus"));
    TEST_ASSERT_EQUAL_INT(SHAPER_OP_UNKNOWN, shaper_op_from_method("shim.lock")); /* not ours */
    TEST_ASSERT_EQUAL_INT(SHAPER_OP_UNKNOWN, shaper_op_from_method(NULL));
}

static void test_method_name_roundtrip(void) {
    TEST_ASSERT_EQUAL_STRING("shaper.anchor.load", shaper_op_method_name(SHAPER_OP_ANCHOR_LOAD));
    TEST_ASSERT_EQUAL_STRING("shaper.pace", shaper_op_method_name(SHAPER_OP_PACE));
    TEST_ASSERT_EQUAL_STRING("shaper.anchor.remove", shaper_op_method_name(SHAPER_OP_ANCHOR_REMOVE));
    TEST_ASSERT_NULL(shaper_op_method_name(SHAPER_OP_UNKNOWN));
}

static void test_execute_known_op_is_failopen_noop(void) {
    int did_noop = 0;
    TEST_ASSERT_EQUAL_INT(SHAPER_OK, shaper_execute(SHAPER_OP_ANCHOR_LOAD, &did_noop));
    TEST_ASSERT_EQUAL_INT(1, did_noop); /* touched nothing — fail-OPEN by construction */
    did_noop = 0;
    TEST_ASSERT_EQUAL_INT(SHAPER_OK, shaper_execute(SHAPER_OP_PACE, &did_noop));
    TEST_ASSERT_EQUAL_INT(1, did_noop);
    did_noop = 0;
    TEST_ASSERT_EQUAL_INT(SHAPER_OK, shaper_execute(SHAPER_OP_ANCHOR_REMOVE, &did_noop));
    TEST_ASSERT_EQUAL_INT(1, did_noop);
}

static void test_execute_unknown_op_notfound(void) {
    int did_noop = 1;
    TEST_ASSERT_EQUAL_INT(SHAPER_ERR_NOTFOUND, shaper_execute(SHAPER_OP_UNKNOWN, &did_noop));
    TEST_ASSERT_EQUAL_INT(0, did_noop);
    TEST_ASSERT_EQUAL_INT(SHAPER_OK, shaper_execute(SHAPER_OP_PACE, NULL)); /* NULL did_noop ok */
}

void run_shaper_tests(void) {
    RUN_TEST(test_method_maps_to_op);
    RUN_TEST(test_unknown_method_is_rejected);
    RUN_TEST(test_method_name_roundtrip);
    RUN_TEST(test_execute_known_op_is_failopen_noop);
    RUN_TEST(test_execute_unknown_op_notfound);
}
