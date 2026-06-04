/* Smoke test — proves the Unity harness builds and runs.
 * Real engine tests (perturb/profile/exclude/stats/rng) replace this in RED.
 */
#include "unity.h"

void setUp(void) {}
void tearDown(void) {}

static void test_toolchain_smoke(void) { TEST_ASSERT_EQUAL_INT(2, 1 + 1); }

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_toolchain_smoke);
    return UNITY_END();
}
