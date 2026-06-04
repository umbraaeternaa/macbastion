/* RED-B contract for schedule. Fails against the stubs until GREEN. */
#include "unity.h"

#include "schedule.h"

static void test_hour_bucket_epoch(void) {
    /* 1970-01-01 00:00:00 UTC -> hour 0 */
    TEST_ASSERT_EQUAL_INT(0, schedule_hour_bucket(0));
}

static void test_hour_bucket_known(void) {
    /* 1609506000 = 2021-01-01 13:00:00 UTC -> hour 13 */
    TEST_ASSERT_EQUAL_INT(13, schedule_hour_bucket(1609506000));
}

static void test_hour_bucket_in_range(void) {
    int h = schedule_hour_bucket(1609552800);
    TEST_ASSERT_TRUE(h >= 0 && h <= 23);
}

static void test_jitter_floor_50(void) {
    uint64_t rng = 42;
    long j = schedule_jitter_ms(10.0, 5.0, &rng); /* tiny base -> floored at 50 */
    TEST_ASSERT_TRUE(j >= 50);
}

static void test_jitter_deterministic(void) {
    uint64_t r1 = 7, r2 = 7;
    long a = schedule_jitter_ms(500.0, 100.0, &r1);
    long b = schedule_jitter_ms(500.0, 100.0, &r2);
    TEST_ASSERT_TRUE(a >= 50); /* a real gap, not the stub's 0 */
    TEST_ASSERT_EQUAL_INT(a, b);
}

static void test_jitter_mean_near_base(void) {
    uint64_t rng = 123;
    double sum = 0.0;
    const int n = 2000;
    for (int i = 0; i < n; i++) {
        sum += (double)schedule_jitter_ms(800.0, 100.0, &rng);
    }
    double mean = sum / n;
    TEST_ASSERT_TRUE(mean > 700.0 && mean < 900.0);
}

void run_schedule_tests(void) {
    RUN_TEST(test_hour_bucket_epoch);
    RUN_TEST(test_hour_bucket_known);
    RUN_TEST(test_hour_bucket_in_range);
    RUN_TEST(test_jitter_floor_50);
    RUN_TEST(test_jitter_deterministic);
    RUN_TEST(test_jitter_mean_near_base);
}
