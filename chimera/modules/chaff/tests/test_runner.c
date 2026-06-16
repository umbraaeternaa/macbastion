/* Single Unity entry point. Each module's tests live in test_<x>.c and expose
 * a run_<x>_tests() group function (declared in tests.h). */
#include "unity.h"

#include "tests.h"

void setUp(void) {}
void tearDown(void) {}

int main(void) {
    UNITY_BEGIN();
    run_endpoints_tests();
    run_schedule_tests();
    run_crypto_tests();
    run_db_tests();
    run_jsonrpc_tests();
    run_generation_tests();
    run_profile_tests();
    run_commands_tests();
    return UNITY_END();
}
