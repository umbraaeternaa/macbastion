/* Contract for EWMA smoothing (§3, alpha 0.3). RED: ewma.cpp is stubbed
 * (update returns 0.0, never initializes), so passthrough/smoothing/init fail;
 * reset passes coincidentally (stub never initializes anyway). */
#include "unity.h"

#include "ewma.hpp"

using tether::Ewma;

static void test_first_sample_passthrough(void) {
    Ewma e(0.3);
    TEST_ASSERT_EQUAL_DOUBLE(-50.0, e.update(-50.0));
}

static void test_smooths_second_sample(void) {
    Ewma e(0.3);
    e.update(-50.0);
    /* 0.3*-70 + 0.7*-50 = -56 */
    TEST_ASSERT_DOUBLE_WITHIN(0.001, -56.0, e.update(-70.0));
}

static void test_initialized_after_update(void) {
    Ewma e(0.3);
    TEST_ASSERT_FALSE(e.initialized());
    e.update(-50.0);
    TEST_ASSERT_TRUE(e.initialized());
}

/* Coincidental-pass in RED: the stub never initializes, so reset's "false" holds
 * trivially. Real boundary appears in GREEN. */
static void test_reset_clears_initialized(void) {
    Ewma e(0.3);
    e.update(-50.0);
    e.reset();
    TEST_ASSERT_FALSE(e.initialized());
}

void run_ewma_tests(void) {
    RUN_TEST(test_first_sample_passthrough);
    RUN_TEST(test_smooths_second_sample);
    RUN_TEST(test_initialized_after_update);
    RUN_TEST(test_reset_clears_initialized);
}
