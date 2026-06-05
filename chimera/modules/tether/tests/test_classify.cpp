/* Contract for disappearance classification (§3 anti-weaponization). RED:
 * classify.cpp records history but never computes a verdict (NONE). The
 * still-present case passes coincidentally; FADE/CLEAN_DROP/INSTANT_DROP fail
 * until GREEN. */
#include "unity.h"

#include "classify.hpp"

using tether::Disappearance;
using tether::DisappearanceClassifier;

static int as_int(Disappearance d) { return static_cast<int>(d); }

/* Coincidental-pass in RED (verdict stays NONE while still seen). */
static void test_none_while_present(void) {
    DisappearanceClassifier c;
    c.observe(-50.0, true, false);
    c.observe(-52.0, true, false);
    TEST_ASSERT_EQUAL_INT(as_int(Disappearance::NONE), as_int(c.classify()));
}

static void test_clean_disconnect(void) {
    DisappearanceClassifier c;
    c.observe(-50.0, true, false);
    c.observe(-50.0, false, true); /* clean BLE disconnect */
    TEST_ASSERT_EQUAL_INT(as_int(Disappearance::CLEAN_DROP), as_int(c.classify()));
}

static void test_fade_gradual_decline(void) {
    DisappearanceClassifier c;
    c.observe(-55.0, true, false);
    c.observe(-65.0, true, false);
    c.observe(-78.0, true, false);
    c.observe(-90.0, false, false); /* faded then lost */
    TEST_ASSERT_EQUAL_INT(as_int(Disappearance::FADE), as_int(c.classify()));
}

static void test_instant_drop_suspicious(void) {
    DisappearanceClassifier c;
    c.observe(-45.0, true, false);
    c.observe(-44.0, true, false); /* strong */
    c.observe(0.0, false, false);  /* vanished in one tick, no fade, no clean */
    TEST_ASSERT_EQUAL_INT(as_int(Disappearance::INSTANT_DROP), as_int(c.classify()));
}

void run_classify_tests(void) {
    RUN_TEST(test_none_while_present);
    RUN_TEST(test_clean_disconnect);
    RUN_TEST(test_fade_gradual_decline);
    RUN_TEST(test_instant_drop_suspicious);
}
