/* Single Unity entry point. Each unit's tests live in test_<x>.cpp and expose a
 * run_<x>_tests() group (declared in tests.hpp). setUp/tearDown MUST be extern "C"
 * — unity.c (compiled as C) links them with C linkage. */
#include "unity.h"

#include "tests.hpp"

extern "C" void setUp(void) {}
extern "C" void tearDown(void) {}

int main(void) {
    UNITY_BEGIN();
    run_ewma_tests();
    run_presence_tests();
    run_classify_tests();
    run_escalation_tests();
    run_emit_tests();
    run_commands_tests();
    run_monitor_tests();
    return UNITY_END();
}
