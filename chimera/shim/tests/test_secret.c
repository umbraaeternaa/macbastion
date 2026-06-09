/* Per-boot secret contract (SS-3). RED: secret.c is a zeros/never-equal stub, so generate
 * (two differ) and equal (matches identical) fail until GREEN. */
#include "unity.h"

#include <string.h>

#include "secret.h"

static void test_generate_is_hex_len_and_differs(void) {
    char a[SHIM_SECRET_HEX_LEN + 1];
    char b[SHIM_SECRET_HEX_LEN + 1];
    secret_generate(a);
    secret_generate(b);
    TEST_ASSERT_EQUAL_INT(SHIM_SECRET_HEX_LEN, (int)strlen(a));
    TEST_ASSERT_FALSE(strcmp(a, b) == 0); /* two per-boot secrets differ */
}

static void test_equal_matches_identical(void) {
    char a[SHIM_SECRET_HEX_LEN + 1];
    secret_generate(a);
    char b[SHIM_SECRET_HEX_LEN + 1];
    strcpy(b, a);
    TEST_ASSERT_TRUE(secret_equal(a, b));
}

static void test_equal_rejects_different(void) {
    char a[SHIM_SECRET_HEX_LEN + 1];
    char b[SHIM_SECRET_HEX_LEN + 1];
    memset(a, 'a', SHIM_SECRET_HEX_LEN);
    a[SHIM_SECRET_HEX_LEN] = '\0';
    memset(b, 'a', SHIM_SECRET_HEX_LEN);
    b[SHIM_SECRET_HEX_LEN] = '\0';
    b[0] = 'b';
    TEST_ASSERT_FALSE(secret_equal(a, b));
}

void run_secret_tests(void) {
    RUN_TEST(test_generate_is_hex_len_and_differs);
    RUN_TEST(test_equal_matches_identical);
    RUN_TEST(test_equal_rejects_different);
}
