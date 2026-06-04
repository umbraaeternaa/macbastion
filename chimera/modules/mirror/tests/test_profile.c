/* RED-B contract for profile presets + downgrade (§3). EXACT spec §3 values.
 * Fails against the zeroed-params stub until GREEN. */
#include "unity.h"

#include <string.h>

#include "profile.h"

/* light: mouse 0.5px, click +/-5ms, dwell +/-10ms, flight +/-5ms */
static void test_params_light(void) {
    mirror_profile_params_t p = profile_params(MIRROR_PROFILE_LIGHT);
    TEST_ASSERT_EQUAL_DOUBLE(0.5, p.mouse_sigma);
    TEST_ASSERT_EQUAL_INT(5, p.click_delta);
    TEST_ASSERT_EQUAL_INT(10, p.dwell_delta);
    TEST_ASSERT_EQUAL_INT(5, p.flight_delta);
}

/* medium: mouse 1.0px, click +/-15ms, dwell +/-25ms, flight +/-20ms */
static void test_params_medium(void) {
    mirror_profile_params_t p = profile_params(MIRROR_PROFILE_MEDIUM);
    TEST_ASSERT_EQUAL_DOUBLE(1.0, p.mouse_sigma);
    TEST_ASSERT_EQUAL_INT(15, p.click_delta);
    TEST_ASSERT_EQUAL_INT(25, p.dwell_delta);
    TEST_ASSERT_EQUAL_INT(20, p.flight_delta);
}

/* heavy: mouse 2.0px, click +/-30ms, dwell +/-50ms, flight +/-40ms */
static void test_params_heavy(void) {
    mirror_profile_params_t p = profile_params(MIRROR_PROFILE_HEAVY);
    TEST_ASSERT_EQUAL_DOUBLE(2.0, p.mouse_sigma);
    TEST_ASSERT_EQUAL_INT(30, p.click_delta);
    TEST_ASSERT_EQUAL_INT(50, p.dwell_delta);
    TEST_ASSERT_EQUAL_INT(40, p.flight_delta);
}

/* Secure field forces light regardless of current. Stub returns current -> FAIL. */
static void test_downgrade_secure_forces_light(void) {
    TEST_ASSERT_EQUAL_INT(MIRROR_PROFILE_LIGHT, profile_downgrade(MIRROR_PROFILE_HEAVY, true));
    TEST_ASSERT_EQUAL_INT(MIRROR_PROFILE_LIGHT, profile_downgrade(MIRROR_PROFILE_MEDIUM, true));
}

/* Non-secure field leaves the profile unchanged. Stub returns current ->
 * passes coincidentally; locks the no-op-on-normal-field contract. */
static void test_downgrade_nonsecure_unchanged(void) {
    TEST_ASSERT_EQUAL_INT(MIRROR_PROFILE_HEAVY, profile_downgrade(MIRROR_PROFILE_HEAVY, false));
}

/* Wire-name round trip. Stub to_str returns NULL / from_str returns -1 -> FAIL. */
static void test_str_roundtrip(void) {
    TEST_ASSERT_NOT_NULL(profile_to_str(MIRROR_PROFILE_MEDIUM));
    TEST_ASSERT_EQUAL_STRING("medium", profile_to_str(MIRROR_PROFILE_MEDIUM));
    TEST_ASSERT_EQUAL_INT(MIRROR_PROFILE_HEAVY, profile_from_str("heavy"));
    TEST_ASSERT_EQUAL_INT(MIRROR_PROFILE_LIGHT, profile_from_str("light"));
}

void run_profile_tests(void) {
    RUN_TEST(test_params_light);
    RUN_TEST(test_params_medium);
    RUN_TEST(test_params_heavy);
    RUN_TEST(test_downgrade_secure_forces_light);
    RUN_TEST(test_downgrade_nonsecure_unchanged);
    RUN_TEST(test_str_roundtrip);
}
