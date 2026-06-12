/* Per-file Unity test-group runners, invoked by test_runner.cpp's single main().
 * Plain C++ linkage — these are called from the C++ main(); only setUp/tearDown
 * need extern "C" (unity.c links them as C). */
#ifndef TETHER_TESTS_HPP
#define TETHER_TESTS_HPP

void run_ewma_tests(void);
void run_presence_tests(void);
void run_classify_tests(void);
void run_escalation_tests(void);
void run_emit_tests(void);
void run_commands_tests(void);
void run_monitor_tests(void);
void run_source_tests(void);

#endif /* TETHER_TESTS_HPP */
