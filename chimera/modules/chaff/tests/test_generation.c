/* RED-B contract for generation decision logic. Fails against stubs until GREEN.
 * Uses a literal endpoint list so it does not depend on endpoints_parse. */
#include "unity.h"

#include "generation.h"

static endpoint_t G_ITEMS[] = {
    {(char *)"https://a.com", (char *)"news"},
    {(char *)"https://b.com", (char *)"dev"},
    {(char *)"https://c.com", (char *)"dev"},
};
static const endpoint_list_t G_LIST = {G_ITEMS, 3};

static void test_target_volume(void) {
    TEST_ASSERT_EQUAL_DOUBLE(50.0, generation_target_volume(5.0, 10.0));
}

static void test_should_send_logic(void) {
    TEST_ASSERT_TRUE(generation_should_send(10.0, 100.0));   /* owed more */
    TEST_ASSERT_FALSE(generation_should_send(100.0, 100.0)); /* quota met */
}

static void test_plan_returns_ok(void) {
    uint64_t rng = 555;
    gen_plan_t plan = {0};
    TEST_ASSERT_EQUAL_INT(CHAFF_OK,
                          generation_plan_next(&G_LIST, "dev", 500.0, &rng, &plan));
}

static void test_plan_endpoint_in_category(void) {
    uint64_t rng = 555;
    gen_plan_t plan = {0};
    TEST_ASSERT_EQUAL_INT(CHAFF_OK,
                          generation_plan_next(&G_LIST, "dev", 500.0, &rng, &plan));
    TEST_ASSERT_NOT_NULL(plan.endpoint);
    TEST_ASSERT_EQUAL_STRING("dev", plan.endpoint->category);
}

static void test_plan_jitter_floored(void) {
    uint64_t rng = 555;
    gen_plan_t plan = {0};
    TEST_ASSERT_EQUAL_INT(CHAFF_OK,
                          generation_plan_next(&G_LIST, "dev", 10.0, &rng, &plan));
    TEST_ASSERT_TRUE(plan.jitter_ms >= 50);
}

static void test_weighted_pick_degenerate(void) {
    uint64_t rng = 12345;
    double w_first[5] = {1.0, 0, 0, 0, 0};
    double w_last[5] = {0, 0, 0, 0, 1.0};
    for (int i = 0; i < 8; i++) { /* a single non-zero weight -> always that index */
        TEST_ASSERT_EQUAL_INT(0, chaff_weighted_category(w_first, 5, &rng));
        TEST_ASSERT_EQUAL_INT(4, chaff_weighted_category(w_last, 5, &rng));
    }
}

static void test_weighted_pick_fallback_uniform(void) {
    uint64_t rng = 999;
    double zero[5] = {0, 0, 0, 0, 0};
    for (int i = 0; i < 8; i++) { /* all-zero (no profile) -> a valid uniform index */
        int idx = chaff_weighted_category(zero, 5, &rng);
        TEST_ASSERT_TRUE(idx >= 0 && idx < 5);
    }
    TEST_ASSERT_EQUAL_INT(0, chaff_weighted_category(NULL, 5, &rng)); /* NULL -> 0, no crash */
}

static void test_weighted_pick_favours_heavy(void) {
    uint64_t rng = 4242;
    double w[5] = {0.9, 0.1, 0, 0, 0};
    int c0 = 0, c1 = 0, other = 0;
    for (int i = 0; i < 2000; i++) {
        int idx = chaff_weighted_category(w, 5, &rng);
        if (idx == 0) {
            c0++;
        } else if (idx == 1) {
            c1++;
        } else {
            other++;
        }
    }
    TEST_ASSERT_EQUAL_INT(0, other); /* never picks a zero-weight category */
    TEST_ASSERT_TRUE(c0 > c1);       /* heavier weight dominates */
}

void run_generation_tests(void) {
    RUN_TEST(test_target_volume);
    RUN_TEST(test_should_send_logic);
    RUN_TEST(test_plan_returns_ok);
    RUN_TEST(test_plan_endpoint_in_category);
    RUN_TEST(test_plan_jitter_floored);
    RUN_TEST(test_weighted_pick_degenerate);
    RUN_TEST(test_weighted_pick_fallback_uniform);
    RUN_TEST(test_weighted_pick_favours_heavy);
}
