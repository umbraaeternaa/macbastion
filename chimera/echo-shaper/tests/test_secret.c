/* A1 EP-5: the per-boot secret — CSPRNG hex generation + constant-time compare. Hermetic. */
#include <stddef.h>
#include <string.h>

#include "unity.h"

#include "secret.h"
#include "tests.h"

static void test_generate_format_and_distinct(void) {
    char a[SHAPER_SECRET_HEX_LEN + 1];
    char b[SHAPER_SECRET_HEX_LEN + 1];
    shaper_secret_generate(a);
    shaper_secret_generate(b);
    TEST_ASSERT_EQUAL_INT(SHAPER_SECRET_HEX_LEN, (int)strlen(a));
    TEST_ASSERT_EQUAL_INT(SHAPER_SECRET_HEX_LEN, (int)strlen(b));
    for (int i = 0; i < SHAPER_SECRET_HEX_LEN; i++) {
        char c = a[i];
        TEST_ASSERT_TRUE((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')); /* lowercase hex */
    }
    TEST_ASSERT_TRUE(strcmp(a, b) != 0); /* two CSPRNG secrets differ */
}

static void test_equal_full_length_compare(void) {
    char a[SHAPER_SECRET_HEX_LEN + 1];
    shaper_secret_generate(a);
    char same[SHAPER_SECRET_HEX_LEN + 1];
    strcpy(same, a);
    TEST_ASSERT_EQUAL_INT(1, shaper_secret_equal(a, same)); /* identical */

    char diff_first[SHAPER_SECRET_HEX_LEN + 1];
    strcpy(diff_first, a);
    diff_first[0] = (a[0] == '0') ? '1' : '0';
    TEST_ASSERT_EQUAL_INT(0, shaper_secret_equal(a, diff_first)); /* first char differs */

    char diff_last[SHAPER_SECRET_HEX_LEN + 1];
    strcpy(diff_last, a);
    diff_last[SHAPER_SECRET_HEX_LEN - 1] = (a[SHAPER_SECRET_HEX_LEN - 1] == '0') ? '1' : '0';
    TEST_ASSERT_EQUAL_INT(0, shaper_secret_equal(a, diff_last)); /* last char differs (full scan) */
}

void run_secret_tests(void) {
    RUN_TEST(test_generate_format_and_distinct);
    RUN_TEST(test_equal_full_length_compare);
}
