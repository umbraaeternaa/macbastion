/* GREEN contract for the ECHO config core (EC-1…EC-4) — the 7 asserts are unchanged from
 * RED. Pins: §3 defaults, range validation, atomic partial set, the shaper bridge. */
#include "unity.h"

#include "config.h"

static void test_config_defaults(void) {
    echo_config_t d = echo_config_default();
    TEST_ASSERT_EQUAL_INT(100, d.target_kbps);
    TEST_ASSERT_EQUAL_INT(200, d.burst_tolerance);
}

static void test_valid_accepts_in_range(void) {
    TEST_ASSERT_EQUAL_INT(1, echo_config_valid(100, 200));
    TEST_ASSERT_EQUAL_INT(1, echo_config_valid(ECHO_MIN_KBPS, ECHO_MIN_BURST));
    TEST_ASSERT_EQUAL_INT(1, echo_config_valid(ECHO_MAX_KBPS, ECHO_MAX_BURST));
}

static void test_valid_rejects_out_of_range(void) {
    TEST_ASSERT_EQUAL_INT(0, echo_config_valid(0, 200));          /* rate too low */
    TEST_ASSERT_EQUAL_INT(0, echo_config_valid(ECHO_MAX_KBPS + 1, 200)); /* too high */
    TEST_ASSERT_EQUAL_INT(0, echo_config_valid(100, -1));         /* burst negative */
    TEST_ASSERT_EQUAL_INT(0, echo_config_valid(100, ECHO_MAX_BURST + 1));
}

static void test_set_applies_both(void) {
    echo_config_t cfg = echo_config_default();
    int t = 500, b = 300;
    TEST_ASSERT_EQUAL_INT(0, echo_config_set(&cfg, &t, &b));
    TEST_ASSERT_EQUAL_INT(500, cfg.target_kbps);
    TEST_ASSERT_EQUAL_INT(300, cfg.burst_tolerance);
}

static void test_set_partial_rate_only(void) {
    echo_config_t cfg = echo_config_default();
    int t = 500;
    TEST_ASSERT_EQUAL_INT(0, echo_config_set(&cfg, &t, NULL));
    TEST_ASSERT_EQUAL_INT(500, cfg.target_kbps);
    TEST_ASSERT_EQUAL_INT(200, cfg.burst_tolerance); /* unchanged */
}

static void test_set_rejects_invalid_atomic(void) {
    echo_config_t cfg = echo_config_default();
    int bad = 0; /* below ECHO_MIN_KBPS */
    TEST_ASSERT_EQUAL_INT(-1, echo_config_set(&cfg, &bad, NULL));
    TEST_ASSERT_EQUAL_INT(100, cfg.target_kbps);     /* untouched (atomic) */
    TEST_ASSERT_EQUAL_INT(200, cfg.burst_tolerance);
}

static void test_config_budget_bridge(void) {
    echo_config_t cfg = echo_config_default(); /* 100 kbps */
    TEST_ASSERT_EQUAL_INT(1024, echo_config_budget(cfg, 10)); /* 100KB/s @10ms */
}

void run_config_tests(void) {
    RUN_TEST(test_config_defaults);
    RUN_TEST(test_valid_accepts_in_range);
    RUN_TEST(test_valid_rejects_out_of_range);
    RUN_TEST(test_set_applies_both);
    RUN_TEST(test_set_partial_rate_only);
    RUN_TEST(test_set_rejects_invalid_atomic);
    RUN_TEST(test_config_budget_bridge);
}
