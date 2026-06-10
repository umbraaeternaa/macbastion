/* Single Unity entry point. Each unit's tests live in test_<x>.c and expose a
 * run_<x>_tests() group function (declared in tests.h). */
#include "unity.h"

#include "ops.h"
#include "shim.h"
#include "tests.h"

/* Global safety: no test may ever fire a REAL op effect (pmset sleeps the display; evict
 * deletes Keychain items). Before every test, swap both actions to harmless stand-ins;
 * the per-op tests inject their own recording stand-ins. */
static shim_result_t safe_lock(void) {
    return SHIM_OK;
}
static shim_result_t safe_evict(void) {
    return SHIM_OK;
}
static shim_result_t safe_reboot(void) {
    return SHIM_OK;
}

void setUp(void) {
    ops_set_lock_action(safe_lock);
    ops_set_evict_action(safe_evict);
    ops_set_reboot_action(safe_reboot);
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
