/* Per-file Unity test-group runners, invoked by test_runner.c's single main(). */
#ifndef MIRROR_TESTS_H
#define MIRROR_TESTS_H

void run_perturb_tests(void);
void run_profile_tests(void);
void run_exclude_tests(void);
void run_stats_tests(void);
void run_rng_tests(void);
void run_jsonrpc_tests(void);
void run_commands_tests(void);

#endif /* MIRROR_TESTS_H */
