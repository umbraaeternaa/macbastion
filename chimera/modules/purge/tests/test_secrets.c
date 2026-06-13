/* PG-secrets: the sensitive-region registry + the real tier3 RAM-wipe action.
 *   - a registered throwaway buffer is actually zeroed by purge_secret_clear_all;
 *   - an empty registry is a safe no-op;
 *   - the registry refuses NULL/zero-length and caps at PURGE_SECRET_MAX.
 * Hermetic — heap/stack buffers only; nothing on disk, nothing of the operator's. */
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#include "unity.h"

#include "secrets.h"
#include "tests.h"

static void test_register_then_clear_zeroes_buffer(void) {
    purge_secret_reset();
    unsigned char *buf = malloc(64);
    TEST_ASSERT_NOT_NULL(buf);
    memset(buf, 0xAA, 64);
    TEST_ASSERT_EQUAL_INT(0, purge_secret_register(buf, 64));
    TEST_ASSERT_EQUAL_INT(1, (int)purge_secret_count());
    TEST_ASSERT_EQUAL_INT(0, purge_secret_clear_all());
    for (int i = 0; i < 64; i++) {
        TEST_ASSERT_EQUAL_UINT8(0x00, buf[i]); /* really zeroed in RAM */
    }
    free(buf);
    purge_secret_reset();
}

static void test_register_refuses_null_and_zero(void) {
    purge_secret_reset();
    unsigned char x = 0xAA;
    TEST_ASSERT_EQUAL_INT(-1, purge_secret_register(NULL, 16));
    TEST_ASSERT_EQUAL_INT(-1, purge_secret_register(&x, 0));
    TEST_ASSERT_EQUAL_INT(0, (int)purge_secret_count());
    purge_secret_reset();
}

static void test_registry_caps_at_max(void) {
    purge_secret_reset();
    static unsigned char slots[PURGE_SECRET_MAX + 2];
    for (int i = 0; i < PURGE_SECRET_MAX; i++) {
        TEST_ASSERT_EQUAL_INT(0, purge_secret_register(&slots[i], 1)); /* fills the registry */
    }
    TEST_ASSERT_EQUAL_INT(-1, purge_secret_register(&slots[PURGE_SECRET_MAX], 1)); /* full */
    TEST_ASSERT_EQUAL_INT(PURGE_SECRET_MAX, (int)purge_secret_count());
    purge_secret_reset();
}

static void test_clear_all_empty_is_safe_noop(void) {
    purge_secret_reset();
    TEST_ASSERT_EQUAL_INT(0, purge_secret_clear_all()); /* nothing registered -> safe */
    purge_secret_reset();
}

void run_secrets_tests(void) {
    RUN_TEST(test_register_then_clear_zeroes_buffer);
    RUN_TEST(test_register_refuses_null_and_zero);
    RUN_TEST(test_registry_caps_at_max);
    RUN_TEST(test_clear_all_empty_is_safe_noop);
}
