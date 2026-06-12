/* RED contract for the per-minute USER-input aggregator (PULSE group-A producer,
 * slice 1). Fails against the no-op stub until GREEN. Privacy: counts only. */
#include "unity.h"

#include "inputagg.h"

/* reset zeroes a dirty window. Stub no-op -> stays dirty -> FAIL. */
static void test_reset_zeroes_dirty_window(void) {
    mirror_inputagg_t a;
    a.chars = 99;
    a.deletes = 7;
    inputagg_reset(&a);
    TEST_ASSERT_EQUAL_UINT64(0, a.chars);
    TEST_ASSERT_EQUAL_UINT64(0, a.deletes);
}

/* printable keystrokes accumulate as chars. Stub -> 0 -> FAIL. */
static void test_chars_counted(void) {
    mirror_inputagg_t a = {0};
    for (int i = 0; i < 5; i++) {
        inputagg_key(&a, 0);
    }
    TEST_ASSERT_EQUAL_UINT64(5, a.chars);
    TEST_ASSERT_EQUAL_UINT64(0, a.deletes);
}

/* deletes count on their own axis. Stub -> 0 -> FAIL. */
static void test_deletes_counted_separately(void) {
    mirror_inputagg_t a = {0};
    inputagg_key(&a, 0);
    inputagg_key(&a, 1);
    inputagg_key(&a, 1);
    TEST_ASSERT_EQUAL_UINT64(1, a.chars);
    TEST_ASSERT_EQUAL_UINT64(2, a.deletes);
}

/* roll snapshots the window into out, then resets the live window. Stub -> out stays
 * 0 (FAIL) and the window is never reset. */
static void test_roll_snapshots_then_resets(void) {
    mirror_inputagg_t a = {0};
    inputagg_key(&a, 0);
    inputagg_key(&a, 0);
    inputagg_key(&a, 1);
    mirror_inputagg_t out = {0};
    inputagg_roll(&a, &out);
    TEST_ASSERT_EQUAL_UINT64(2, out.chars);   /* the window's chars */
    TEST_ASSERT_EQUAL_UINT64(1, out.deletes); /* the window's deletes */
    TEST_ASSERT_EQUAL_UINT64(0, a.chars);     /* live window reset for next minute */
    TEST_ASSERT_EQUAL_UINT64(0, a.deletes);
}

void run_inputagg_tests(void) {
    RUN_TEST(test_reset_zeroes_dirty_window);
    RUN_TEST(test_chars_counted);
    RUN_TEST(test_deletes_counted_separately);
    RUN_TEST(test_roll_snapshots_then_resets);
}
