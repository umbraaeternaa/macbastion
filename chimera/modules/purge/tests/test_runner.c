/* Single Unity entry point. Each module's tests live in test_<x>.c and expose a
 * run_<x>_tests() group function (declared in tests.h). */
#include "unity.h"

#include "tests.h"

void setUp(void) {}
void tearDown(void) {}

int main(void) {
    UNITY_BEGIN();
    run_plan_tests();
    run_targets_tests();
    return UNITY_END();
}
