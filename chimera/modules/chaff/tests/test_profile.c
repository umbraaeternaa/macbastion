/* Phase-A profile parse tests. The file I/O (chaff_profile_load) is manual-tier; the JSON ->
 * weights mapping is pure + tested here. */
#include "unity.h"

#include "profile.h"
#include "tests.h"

static void test_parse_valid_in_category_order(void) {
    double w[CHAFF_NUM_CATEGORIES] = {0};
    const char *j =
        "{\"categories\":{\"news\":0.1,\"tech\":0.2,\"social\":0.3,\"search\":0.25,\"dev\":0.15}}";
    TEST_ASSERT_TRUE(chaff_profile_parse(j, w));
    TEST_ASSERT_EQUAL_DOUBLE(0.1, w[0]);   /* news */
    TEST_ASSERT_EQUAL_DOUBLE(0.2, w[1]);   /* tech */
    TEST_ASSERT_EQUAL_DOUBLE(0.3, w[2]);   /* social */
    TEST_ASSERT_EQUAL_DOUBLE(0.25, w[3]);  /* search */
    TEST_ASSERT_EQUAL_DOUBLE(0.15, w[4]);  /* dev */
}

static void test_parse_missing_key_is_zero(void) {
    double w[CHAFF_NUM_CATEGORIES] = {9, 9, 9, 9, 9};
    TEST_ASSERT_TRUE(chaff_profile_parse("{\"categories\":{\"search\":0.7}}", w));
    TEST_ASSERT_EQUAL_DOUBLE(0.7, w[3]);  /* present */
    TEST_ASSERT_EQUAL_DOUBLE(0.0, w[0]);  /* absent -> 0 */
}

static void test_parse_rejects_invalid(void) {
    double w[CHAFF_NUM_CATEGORIES] = {0};
    TEST_ASSERT_FALSE(chaff_profile_parse("{\"hourly\":[]}", w));  /* no categories object */
    TEST_ASSERT_FALSE(chaff_profile_parse("not json", w));
    TEST_ASSERT_FALSE(chaff_profile_parse(NULL, w));
}

void run_profile_tests(void) {
    RUN_TEST(test_parse_valid_in_category_order);
    RUN_TEST(test_parse_missing_key_is_zero);
    RUN_TEST(test_parse_rejects_invalid);
}
