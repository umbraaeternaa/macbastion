/* Contract for companion pinning (anti-spoof, TE-pin). RED: pin.cpp trusts any non-empty
 * device (no pinning), so the impostor-rejection + paired-state contracts FAIL; the
 * empty-id, first-sight and same-device cases pass coincidentally until GREEN. */
#include "unity.h"

#include "pin.hpp"

using tether::CompanionPin;

/* No device -> never the companion (MANIFESTO §4). Coincidental pass in RED. */
static void test_empty_never_matches(void) {
    CompanionPin p;
    TEST_ASSERT_FALSE(p.accept(""));
    TEST_ASSERT_FALSE(p.paired());
}

/* The first non-empty device seen becomes the pinned companion. */
static void test_first_device_pins(void) {
    CompanionPin p;
    TEST_ASSERT_TRUE(p.accept("A8:79:8D:90:1C:83"));
    TEST_ASSERT_TRUE(p.paired()); /* FAILS in RED (pin state not recorded) */
}

/* The same device keeps matching, regardless of address formatting. */
static void test_same_device_matches(void) {
    CompanionPin p;
    p.accept("A8:79:8D:90:1C:83");
    TEST_ASSERT_TRUE(p.accept("a8798d901c83")); /* normalised-equal */
}

/* THE ANTI-SPOOF CORE: a different device advertising the same UUID is rejected. */
static void test_impostor_rejected(void) {
    CompanionPin p;
    p.accept("A8:79:8D:90:1C:83");                    /* pin the real companion */
    TEST_ASSERT_FALSE(p.accept("11:22:33:44:55:66")); /* FAILS in RED (impostor trusted) */
}

/* unpair() forgets the pin; the next device re-pins (new phone). */
static void test_unpair_repins(void) {
    CompanionPin p;
    p.accept("A8:79:8D:90:1C:83");
    p.unpair();
    TEST_ASSERT_FALSE(p.paired());                    /* FAILS in RED */
    TEST_ASSERT_TRUE(p.accept("11:22:33:44:55:66"));  /* the new device pins */
    TEST_ASSERT_EQUAL_STRING("112233445566", p.pinned().c_str()); /* FAILS in RED */
}

void run_pin_tests(void) {
    RUN_TEST(test_empty_never_matches);
    RUN_TEST(test_first_device_pins);
    RUN_TEST(test_same_device_matches);
    RUN_TEST(test_impostor_rejected);
    RUN_TEST(test_unpair_repins);
}
