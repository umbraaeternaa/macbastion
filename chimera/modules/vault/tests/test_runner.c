/* Single Unity entry point. Each unit's tests live in test_<x>.c and expose a
 * run_<x>_tests() group function (declared in tests.h). */
#include "unity.h"

#include "tests.h"

void setUp(void) {}
void tearDown(void) {}

int main(void) {
    UNITY_BEGIN();
    run_lexer_tests();
    run_parser_tests();
    run_evaluator_tests();
    run_fail_closed_tests();
    run_relock_tests();
    run_decide_tests();
    return UNITY_END();
}
