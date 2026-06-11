/* Single Unity entry point. Each unit's tests live in test_<x>.c and expose a
 * run_<x>_tests() group function (declared in tests.h). */
#include "unity.h"

#include "tests.h"

/* Before every test, swap the keychain + mount to in-memory / temp-dir backends so NO test ever
 * touches the real login Keychain or mounts a real RAM disk (both real paths are manual-tier). */
void setUp(void) {
    vault_test_install_mem_keychain();
    vault_test_install_tmp_mount();
}
void tearDown(void) {}

int main(void) {
    UNITY_BEGIN();
    run_lexer_tests();
    run_parser_tests();
    run_evaluator_tests();
    run_fail_closed_tests();
    run_relock_tests();
    run_decide_tests();
    run_crypto_tests();
    run_commands_tests();
    run_keychain_tests();
    run_unlock_tests();
    run_mount_tests();
    return UNITY_END();
}
