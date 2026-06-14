/* Per-file Unity test-group runners, invoked by test_runner.c's single main(). */
#ifndef SHAPER_TESTS_H
#define SHAPER_TESTS_H

void run_shaper_tests(void);
void run_anchor_tests(void);
void run_protocol_tests(void);
void run_peercred_tests(void);
void run_server_tests(void);
void run_secret_tests(void);
void run_ownership_tests(void);

#endif /* SHAPER_TESTS_H */
