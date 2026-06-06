/* Per-file Unity test-group runners, invoked by test_runner.c's single main(). */
#ifndef VAULT_TESTS_H
#define VAULT_TESTS_H

void run_lexer_tests(void);
void run_parser_tests(void);
void run_evaluator_tests(void);
void run_fail_closed_tests(void);
void run_relock_tests(void);

#endif /* VAULT_TESTS_H */
