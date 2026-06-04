/* RED-B contract for the exclusion list (§3, §5 mirror.exclude.*). Fails against
 * the match-misses / mutations-error stub until GREEN. */
#include "unity.h"

#include "exclude.h"

/* Add then match -> hit. Stub add errors + match misses -> FAIL. */
static void test_match_hit(void) {
    exclusion_list_t list = {0};
    TEST_ASSERT_EQUAL_INT(MIRROR_OK, exclude_add(&list, "com.apple.Terminal"));
    TEST_ASSERT_TRUE(exclude_match(&list, "com.apple.Terminal"));
}

/* Empty list never matches. Stub returns false -> passes coincidentally. */
static void test_match_miss(void) {
    exclusion_list_t list = {0};
    TEST_ASSERT_FALSE(exclude_match(&list, "com.apple.Terminal"));
}

/* Add bumps count to 1. Stub errors, count stays 0 -> FAIL. */
static void test_add_increments_count(void) {
    exclusion_list_t list = {0};
    TEST_ASSERT_EQUAL_INT(MIRROR_OK, exclude_add(&list, "com.foo.Bar"));
    TEST_ASSERT_EQUAL_UINT(1, list.count);
}

/* Re-adding the same id is idempotent (count stays 1). Stub -> count 0 -> FAIL. */
static void test_add_dedup(void) {
    exclusion_list_t list = {0};
    exclude_add(&list, "com.foo.Bar");
    exclude_add(&list, "com.foo.Bar");
    TEST_ASSERT_EQUAL_UINT(1, list.count);
}

/* Remove drops it: count back to 0 and match misses. Stub -> FAIL. */
static void test_remove(void) {
    exclusion_list_t list = {0};
    exclude_add(&list, "com.foo.Bar");
    TEST_ASSERT_EQUAL_INT(MIRROR_OK, exclude_remove(&list, "com.foo.Bar"));
    TEST_ASSERT_EQUAL_UINT(0, list.count);
    TEST_ASSERT_FALSE(exclude_match(&list, "com.foo.Bar"));
}

void run_exclude_tests(void) {
    RUN_TEST(test_match_hit);
    RUN_TEST(test_match_miss);
    RUN_TEST(test_add_increments_count);
    RUN_TEST(test_add_dedup);
    RUN_TEST(test_remove);
}
