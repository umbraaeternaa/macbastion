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

/* a single straight move -> path == straight-line -> ratio 1.0. Stub 0 -> FAIL. */
static void test_mouse_straight_ratio_one(void) {
    mirror_inputagg_t a = {0};
    inputagg_mouse_move(&a, 10.0, 0.0);
    TEST_ASSERT_DOUBLE_WITHIN(0.001, 1.0, inputagg_mouse_ratio(&a));
}

/* right-angle: path 10+10=20 / straight sqrt(200)=14.142 -> 1.41421. Stub 0 -> FAIL. */
static void test_mouse_right_angle_ratio(void) {
    mirror_inputagg_t a = {0};
    inputagg_mouse_move(&a, 10.0, 0.0);
    inputagg_mouse_move(&a, 0.0, 10.0);
    TEST_ASSERT_DOUBLE_WITHIN(0.001, 1.41421, inputagg_mouse_ratio(&a));
}

/* no movement -> ratio 0.0 (absent). Passes against the stub (still a valid contract). */
static void test_mouse_no_movement_absent(void) {
    mirror_inputagg_t a = {0};
    TEST_ASSERT_DOUBLE_WITHIN(0.0001, 0.0, inputagg_mouse_ratio(&a));
}

/* back-and-forth: net ~0 -> floored -> ratio capped at MAX (10.0). Stub 0 -> FAIL. */
static void test_mouse_backtrack_ratio_capped(void) {
    mirror_inputagg_t a = {0};
    inputagg_mouse_move(&a, 100.0, 0.0);
    inputagg_mouse_move(&a, -100.0, 0.0);
    TEST_ASSERT_DOUBLE_WITHIN(0.001, MIRROR_MOUSE_RATIO_MAX, inputagg_mouse_ratio(&a));
}

/* roll clears the mouse window too. */
static void test_roll_clears_mouse(void) {
    mirror_inputagg_t a = {0};
    inputagg_mouse_move(&a, 10.0, 0.0);
    mirror_inputagg_t out = {0};
    inputagg_roll(&a, &out);
    TEST_ASSERT_DOUBLE_WITHIN(0.0001, 0.0, inputagg_mouse_ratio(&a));
}

void run_inputagg_tests(void) {
    RUN_TEST(test_reset_zeroes_dirty_window);
    RUN_TEST(test_chars_counted);
    RUN_TEST(test_deletes_counted_separately);
    RUN_TEST(test_roll_snapshots_then_resets);
    RUN_TEST(test_mouse_straight_ratio_one);
    RUN_TEST(test_mouse_right_angle_ratio);
    RUN_TEST(test_mouse_no_movement_absent);
    RUN_TEST(test_mouse_backtrack_ratio_capped);
    RUN_TEST(test_roll_clears_mouse);
}
