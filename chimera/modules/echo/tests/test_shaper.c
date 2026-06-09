/* GREEN contract for the ECHO shaper core (ES-2/ES-3) — the 9 asserts are unchanged from
 * RED. Pins: the budget formula, the constant-rate FLAT-wire invariant, burst drain, clamps. */
#include "unity.h"

#include "shaper.h"

static void test_budget_100kbps_10ms(void) {
    TEST_ASSERT_EQUAL_INT(1024, echo_budget_bytes(100, 10)); /* 100*1024*10/1000 */
}

static void test_budget_nonpositive(void) {
    TEST_ASSERT_EQUAL_INT(0, echo_budget_bytes(0, 10));
    TEST_ASSERT_EQUAL_INT(0, echo_budget_bytes(100, 0));
}

static void test_idle_pads_to_budget(void) {
    echo_decision_t d = echo_shape(0, 1024, 1024);
    TEST_ASSERT_EQUAL_INT(0, d.real_send);
    TEST_ASSERT_EQUAL_INT(1024, d.padding); /* idle -> flat wire of pure padding */
}

static void test_light_pads_the_gap(void) {
    echo_decision_t d = echo_shape(300, 1024, 1024);
    TEST_ASSERT_EQUAL_INT(300, d.real_send);
    TEST_ASSERT_EQUAL_INT(724, d.padding);
}

static void test_exact_no_padding(void) {
    echo_decision_t d = echo_shape(1024, 1024, 1024);
    TEST_ASSERT_EQUAL_INT(1024, d.real_send);
    TEST_ASSERT_EQUAL_INT(0, d.padding);
}

static void test_burst_drains_backlog(void) {
    echo_decision_t d = echo_shape(5000, 1024, 1024);
    TEST_ASSERT_EQUAL_INT(2048, d.real_send); /* budget + burst */
    TEST_ASSERT_EQUAL_INT(0, d.padding);
}

static void test_beyond_burst_capped(void) {
    echo_decision_t d = echo_shape(5000, 1024, 512);
    TEST_ASSERT_EQUAL_INT(1536, d.real_send); /* budget + burst; queue not fully drained */
    TEST_ASSERT_EQUAL_INT(0, d.padding);
}

static void test_flat_wire_invariant(void) {
    long q[] = {0, 100, 500, 1024};
    for (int i = 0; i < 4; i++) {
        echo_decision_t d = echo_shape(q[i], 1024, 1024);
        TEST_ASSERT_EQUAL_INT(1024, d.real_send + d.padding); /* constant wire */
        TEST_ASSERT_TRUE(d.real_send <= q[i]);
        TEST_ASSERT_TRUE(d.padding >= 0);
    }
}

static void test_clamps(void) {
    echo_decision_t neg = echo_shape(-5, 1024, 0);
    TEST_ASSERT_EQUAL_INT(0, neg.real_send);
    TEST_ASSERT_EQUAL_INT(1024, neg.padding);
    echo_decision_t z = echo_shape(100, 0, 0); /* budget <= 0 -> no-op */
    TEST_ASSERT_EQUAL_INT(0, z.real_send);
    TEST_ASSERT_EQUAL_INT(0, z.padding);
}

void run_shaper_tests(void) {
    RUN_TEST(test_budget_100kbps_10ms);
    RUN_TEST(test_budget_nonpositive);
    RUN_TEST(test_idle_pads_to_budget);
    RUN_TEST(test_light_pads_the_gap);
    RUN_TEST(test_exact_no_padding);
    RUN_TEST(test_burst_drains_backlog);
    RUN_TEST(test_beyond_burst_capped);
    RUN_TEST(test_flat_wire_invariant);
    RUN_TEST(test_clamps);
}
