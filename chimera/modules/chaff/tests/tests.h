/* Per-file Unity test-group runners, invoked by test_runner.c's single main(). */
#ifndef CHAFF_TESTS_H
#define CHAFF_TESTS_H

void run_endpoints_tests(void);
void run_schedule_tests(void);
void run_crypto_tests(void);
void run_db_tests(void);
void run_jsonrpc_tests(void);
void run_generation_tests(void);
void run_commands_tests(void);

#endif /* CHAFF_TESTS_H */
