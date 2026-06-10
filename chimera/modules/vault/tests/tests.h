/* Per-file Unity test-group runners, invoked by test_runner.c's single main(). */
#ifndef VAULT_TESTS_H
#define VAULT_TESTS_H

void run_lexer_tests(void);
void run_parser_tests(void);
void run_evaluator_tests(void);
void run_fail_closed_tests(void);
void run_relock_tests(void);
void run_decide_tests(void);
void run_crypto_tests(void);
void run_commands_tests(void);
void run_keychain_tests(void);
void run_unlock_tests(void);

/* test_keychain.c — install an in-memory keychain backend (setUp uses it so no test touches the
 * real login Keychain) + introspect how many master secrets it holds. */
void vault_test_install_mem_keychain(void);
int vault_test_keychain_count(void);

#endif /* VAULT_TESTS_H */
