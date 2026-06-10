/* Single Unity entry point. Each unit's tests live in test_<x>.c and expose a
 * run_<x>_tests() group function (declared in tests.h). */
#include "unity.h"

#include "ops.h"
#include "shim.h"
#include "tests.h"

/* Global safety: no test may ever fire the REAL lock (pmset sleeps the display). Before
 * every test, swap the lock action to a harmless stand-in; lock tests inject their own. */
static shim_result_t safe_lock(void) {
    return SHIM_OK;
}

void setUp(void) {
    ops_set_lock_action(safe_lock);
}
void tearDown(void) {}

int main(void) {
    UNITY_BEGIN();
    run_ops_tests();
    run_peercred_tests();
    run_server_tests();
    run_protocol_tests();
    run_secret_tests();
    run_attest_tests();
    return UNITY_END();
}
