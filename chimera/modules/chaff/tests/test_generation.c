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

void run_generation_tests(void) {
    RUN_TEST(test_target_volume);
    RUN_TEST(test_should_send_logic);
    RUN_TEST(test_plan_returns_ok);
    RUN_TEST(test_plan_endpoint_in_category);
    RUN_TEST(test_plan_jitter_floored);
}
