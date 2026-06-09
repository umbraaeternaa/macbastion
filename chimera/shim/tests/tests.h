/* Per-file Unity test-group runners, invoked by test_runner.c's single main(). */
#ifndef SHIM_TESTS_H
#define SHIM_TESTS_H

void run_ops_tests(void);
void run_peercred_tests(void);
void run_server_tests(void);
void run_protocol_tests(void);
void run_secret_tests(void);

#endif /* SHIM_TESTS_H */
