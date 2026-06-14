/* Single Unity entry point. Each unit's tests live in test_<x>.c and expose a
 * run_<x>_tests() group function (declared in tests.h). */
#include "unity.h"

#include "tests.h"

void setUp(void) {}
void tearDown(void) {}

int main(void) {
    UNITY_BEGIN();
    run_shaper_tests();
    run_anchor_tests();
    run_protocol_tests();
    run_peercred_tests();
    run_server_tests();
    run_secret_tests();
    run_ownership_tests();
    return UNITY_END();
}
