/* RED-B contract for aggregate counters (§7 privacy invariant). Fails against
 * the no-op stub until GREEN. */
#include "unity.h"

#include "stats.h"

/* Fresh stats read zero. Stub get returns 0 -> passes coincidentally. */
static void test_init_zero(void) {
    mirror_stats_t s = {0};
    TEST_ASSERT_EQUAL_UINT64(0, stats_get(&s, MIRROR_EV_MOUSE_MOVE));
}

/* One increment -> count 1. Stub no-op -> get 0 -> FAIL. */
static void test_increment_one(void) {
    mirror_stats_t s = {0};
    stats_increment(&s, MIRROR_EV_KEY_DOWN);
    TEST_ASSERT_EQUAL_UINT64(1, stats_get(&s, MIRROR_EV_KEY_DOWN));
}

/* Repeated increments accumulate (cumulative, no reset). Stub -> 0 -> FAIL. */
static void test_increment_cumulative(void) {
    mirror_stats_t s = {0};
    for (int i = 0; i < 5; i++) {
        stats_increment(&s, MIRROR_EV_MOUSE_CLICK);
    }
    TEST_ASSERT_EQUAL_UINT64(5, stats_get(&s, MIRROR_EV_MOUSE_CLICK));
}

/* Counters are per-type and independent. Stub -> all 0 -> FAIL. */
static void test_distinct_types(void) {
    mirror_stats_t s = {0};
    stats_increment(&s, MIRROR_EV_MOUSE_MOVE);
    stats_increment(&s, MIRROR_EV_SCROLL);
    stats_increment(&s, MIRROR_EV_SCROLL);
    TEST_ASSERT_EQUAL_UINT64(1, stats_get(&s, MIRROR_EV_MOUSE_MOVE));
    TEST_ASSERT_EQUAL_UINT64(2, stats_get(&s, MIRROR_EV_SCROLL));
    TEST_ASSERT_EQUAL_UINT64(0, stats_get(&s, MIRROR_EV_KEY_UP));
}

/* Out-of-range type is ignored, not a crash or stray count. Stub -> 0 -> passes
 * coincidentally; locks the bounds contract. */
static void test_out_of_range_ignored(void) {
    mirror_stats_t s = {0};
    stats_increment(&s, MIRROR_EV__COUNT);
    TEST_ASSERT_EQUAL_UINT64(0, stats_get(&s, MIRROR_EV__COUNT));
}

void run_stats_tests(void) {
    RUN_TEST(test_init_zero);
    RUN_TEST(test_increment_one);
    RUN_TEST(test_increment_cumulative);
    RUN_TEST(test_distinct_types);
    RUN_TEST(test_out_of_range_ignored);
}
