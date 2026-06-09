/* RED contract for the PURGE config core (PC-1…PC-3). Fails against the stub until GREEN.
 * Pins: §4/§8 defaults, post-action parse/format round-trip, atomic partial set. */
#include "unity.h"

#include "config.h"

static void test_defaults(void) {
    purge_config_t c = purge_config_default();
    TEST_ASSERT_EQUAL_INT(PURGE_REBOOT, c.post_action);
    TEST_ASSERT_EQUAL_INT(0, c.marker);
}

static void test_from_str_valid(void) {
    TEST_ASSERT_EQUAL_INT(PURGE_REBOOT, purge_post_action_from_str("reboot"));
    TEST_ASSERT_EQUAL_INT(PURGE_SHUTDOWN, purge_post_action_from_str("shutdown"));
    TEST_ASSERT_EQUAL_INT(PURGE_STAY, purge_post_action_from_str("stay"));
}

static void test_from_str_invalid(void) {
    TEST_ASSERT_EQUAL_INT(-1, purge_post_action_from_str("explode"));
    TEST_ASSERT_EQUAL_INT(-1, purge_post_action_from_str(NULL));
}

static void test_str_roundtrip(void) {
    TEST_ASSERT_EQUAL_STRING("reboot", purge_post_action_str(PURGE_REBOOT));
    TEST_ASSERT_EQUAL_STRING("shutdown", purge_post_action_str(PURGE_SHUTDOWN));
    TEST_ASSERT_EQUAL_STRING("stay", purge_post_action_str(PURGE_STAY));
}

static void test_set_valid(void) {
    purge_config_t c = purge_config_default();
    int m = 1;
    TEST_ASSERT_EQUAL_INT(0, purge_config_set(&c, "stay", &m));
    TEST_ASSERT_EQUAL_INT(PURGE_STAY, c.post_action);
    TEST_ASSERT_EQUAL_INT(1, c.marker);
}

static void test_set_invalid_atomic(void) {
    purge_config_t c = purge_config_default(); /* {REBOOT, 0} */
    TEST_ASSERT_EQUAL_INT(-1, purge_config_set(&c, "nuke", NULL));
    TEST_ASSERT_EQUAL_INT(PURGE_REBOOT, c.post_action); /* untouched */
    TEST_ASSERT_EQUAL_INT(0, c.marker);
}

static void test_set_partial_marker_only(void) {
    purge_config_t c = purge_config_default();
    int m = 1;
    TEST_ASSERT_EQUAL_INT(0, purge_config_set(&c, NULL, &m));
    TEST_ASSERT_EQUAL_INT(PURGE_REBOOT, c.post_action); /* unchanged */
    TEST_ASSERT_EQUAL_INT(1, c.marker);
}

void run_config_tests(void) {
    RUN_TEST(test_defaults);
    RUN_TEST(test_from_str_valid);
    RUN_TEST(test_from_str_invalid);
    RUN_TEST(test_str_roundtrip);
    RUN_TEST(test_set_valid);
    RUN_TEST(test_set_invalid_atomic);
    RUN_TEST(test_set_partial_marker_only);
}
