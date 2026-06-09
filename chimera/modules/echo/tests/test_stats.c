/* GREEN contract for the ECHO stats core (ET-1…ET-3) — the 7 asserts are unchanged from RED.
 * Pins: init-zero, overall padding ratio, per-tick decile histogram, surge trigger, guard. */
#include "unity.h"

#include "stats.h"

static void test_init_zeroes(void) {
    echo_stats_t s;
    s.total_real = 999;
    s.total_padding = 999;
    s.ticks = 999;
    for (int i = 0; i < ECHO_HIST_BINS; i++) {
        s.hist[i] = 999;
    }
    echo_stats_init(&s);
    TEST_ASSERT_EQUAL_INT(0, s.total_real);
    TEST_ASSERT_EQUAL_INT(0, s.total_padding);
    TEST_ASSERT_EQUAL_INT(0, s.ticks);
    for (int i = 0; i < ECHO_HIST_BINS; i++) {
        TEST_ASSERT_EQUAL_INT(0, s.hist[i]);
    }
}

static void test_idle_100pct_bin9(void) {
    echo_stats_t s = {0};
    echo_stats_init(&s);
    echo_stats_record(&s, 0, 1024); /* pure padding -> 100% */
    TEST_ASSERT_EQUAL_INT(100, echo_padding_ratio_pct(&s));
    TEST_ASSERT_EQUAL_INT(1, s.hist[9]);
}

static void test_full_real_0pct_bin0(void) {
    echo_stats_t s = {0};
    echo_stats_init(&s);
    echo_stats_record(&s, 1024, 0); /* pure real -> 0% */
    TEST_ASSERT_EQUAL_INT(0, echo_padding_ratio_pct(&s));
    TEST_ASSERT_EQUAL_INT(1, s.hist[0]);
}

static void test_mixed_overall_ratio(void) {
    echo_stats_t s = {0};
    echo_stats_init(&s);
    echo_stats_record(&s, 300, 700);
    echo_stats_record(&s, 1000, 0);
    /* real=1300, padding=700, wire=2000 -> 35% */
    TEST_ASSERT_EQUAL_INT(35, echo_padding_ratio_pct(&s));
}

static void test_histogram_bins(void) {
    echo_stats_t s = {0};
    echo_stats_init(&s);
    echo_stats_record(&s, 0, 100);   /* 100% -> bin 9 */
    echo_stats_record(&s, 100, 0);   /* 0%   -> bin 0 */
    echo_stats_record(&s, 50, 50);   /* 50%  -> bin 5 */
    TEST_ASSERT_EQUAL_INT(1, s.hist[9]);
    TEST_ASSERT_EQUAL_INT(1, s.hist[0]);
    TEST_ASSERT_EQUAL_INT(1, s.hist[5]);
    TEST_ASSERT_EQUAL_INT(3, s.ticks);
}

static void test_surge_trigger(void) {
    echo_stats_t s = {0};
    echo_stats_init(&s);
    echo_stats_record(&s, 0, 1000); /* 100% */
    TEST_ASSERT_EQUAL_INT(1, echo_padding_surge(&s, 80));
    echo_stats_t s2 = {0};
    echo_stats_init(&s2);
    echo_stats_record(&s2, 1000, 100); /* ~9% */
    TEST_ASSERT_EQUAL_INT(0, echo_padding_surge(&s2, 80));
}

static void test_empty_guard(void) {
    echo_stats_t s = {0};
    echo_stats_init(&s);
    TEST_ASSERT_EQUAL_INT(0, echo_padding_ratio_pct(&s)); /* no div-by-zero */
    TEST_ASSERT_EQUAL_INT(0, echo_padding_surge(&s, 80));
}

void run_stats_tests(void) {
    RUN_TEST(test_init_zeroes);
    RUN_TEST(test_idle_100pct_bin9);
    RUN_TEST(test_full_real_0pct_bin0);
    RUN_TEST(test_mixed_overall_ratio);
    RUN_TEST(test_histogram_bins);
    RUN_TEST(test_surge_trigger);
    RUN_TEST(test_empty_guard);
}
