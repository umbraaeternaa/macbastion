/* RED-B contract for endpoints. Fails against the stubs until GREEN. */
#include "unity.h"

#include "endpoints.h"

static const char *SAMPLE =
    "{\"version\":1,\"categories\":[\"news\",\"dev\"],"
    "\"endpoints\":["
    "{\"url\":\"https://a.com\",\"category\":\"news\"},"
    "{\"url\":\"https://b.com\",\"category\":\"dev\"},"
    "{\"url\":\"https://c.com\",\"category\":\"news\"}]}";

static void test_parse_returns_ok(void) {
    endpoint_list_t *list = NULL;
    TEST_ASSERT_EQUAL_INT(CHAFF_OK, endpoints_parse(SAMPLE, &list));
    endpoints_free(list);
}

static void test_parse_counts_all(void) {
    endpoint_list_t *list = NULL;
    endpoints_parse(SAMPLE, &list);
    TEST_ASSERT_NOT_NULL(list);
    TEST_ASSERT_EQUAL_size_t(3, list->count);
    endpoints_free(list);
}

static void test_parse_malformed_errors(void) {
    endpoint_list_t *list = NULL;
    TEST_ASSERT_EQUAL_INT(CHAFF_ERR_PARSE, endpoints_parse("{ not json", &list));
}

static void test_count_category(void) {
    endpoint_list_t *list = NULL;
    endpoints_parse(SAMPLE, &list);
    TEST_ASSERT_NOT_NULL(list);
    TEST_ASSERT_EQUAL_size_t(2, endpoints_count_category(list, "news"));
    endpoints_free(list);
}

static void test_pick_returns_in_category(void) {
    endpoint_list_t *list = NULL;
    endpoints_parse(SAMPLE, &list);
    uint64_t rng = 12345;
    const endpoint_t *e = endpoints_pick(list, "dev", &rng);
    TEST_ASSERT_NOT_NULL(e);
    TEST_ASSERT_EQUAL_STRING("dev", e->category);
    endpoints_free(list);
}

static void test_pick_deterministic_with_seed(void) {
    endpoint_list_t *list = NULL;
    endpoints_parse(SAMPLE, &list);
    uint64_t r1 = 999, r2 = 999;
    const endpoint_t *a = endpoints_pick(list, "news", &r1);
    const endpoint_t *b = endpoints_pick(list, "news", &r2);
    TEST_ASSERT_NOT_NULL(a);
    TEST_ASSERT_NOT_NULL(b);
    TEST_ASSERT_EQUAL_STRING(a->url, b->url);
    endpoints_free(list);
}

static void test_pick_empty_category_null(void) {
    endpoint_list_t *list = NULL;
    endpoints_parse(SAMPLE, &list);
    uint64_t rng = 1;
    TEST_ASSERT_NULL(endpoints_pick(list, "nonexistent", &rng));
    endpoints_free(list);
}

void run_endpoints_tests(void) {
    RUN_TEST(test_parse_returns_ok);
    RUN_TEST(test_parse_counts_all);
    RUN_TEST(test_parse_malformed_errors);
    RUN_TEST(test_count_category);
    RUN_TEST(test_pick_returns_in_category);
    RUN_TEST(test_pick_deterministic_with_seed);
    RUN_TEST(test_pick_empty_category_null);
}
