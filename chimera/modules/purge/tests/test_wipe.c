/* RED contract for secure memory wipe (§5.8 RAM erase). Fails against the no-op stub
 * until GREEN. */
#include "unity.h"

#include <string.h>

#include "wipe.h"

/* a full buffer of 0xFF goes to all 0x00. Stub no-op -> stays 0xFF -> FAIL. */
static void test_wipe_zeros_buffer(void) {
    unsigned char buf[256];
    memset(buf, 0xFF, sizeof(buf));
    purge_wipe(buf, sizeof(buf));
    for (size_t i = 0; i < sizeof(buf); i++) {
        TEST_ASSERT_EQUAL_HEX8(0x00, buf[i]);
    }
}

/* len == 0 touches nothing. */
static void test_wipe_zero_len_is_noop(void) {
    unsigned char b = 0xAB;
    purge_wipe(&b, 0);
    TEST_ASSERT_EQUAL_HEX8(0xAB, b);
}

/* a partial wipe clears exactly len bytes, never past it. Stub -> head stays 0xFF -> FAIL. */
static void test_wipe_partial_leaves_tail(void) {
    unsigned char buf[8];
    memset(buf, 0xFF, sizeof(buf));
    purge_wipe(buf, 4);
    TEST_ASSERT_EQUAL_HEX8(0x00, buf[0]);
    TEST_ASSERT_EQUAL_HEX8(0x00, buf[3]);
    TEST_ASSERT_EQUAL_HEX8(0xFF, buf[4]); /* untouched past len */
    TEST_ASSERT_EQUAL_HEX8(0xFF, buf[7]);
}

/* PW-2: the DC ZVA block size is a sane power of two. Stub returns 0 -> FAIL. */
static void test_zva_blocksize_sane(void) {
    size_t bs = purge_zva_blocksize();
    TEST_ASSERT_GREATER_OR_EQUAL_UINT(16, bs);   /* >= 16 bytes */
    TEST_ASSERT_LESS_OR_EQUAL_UINT(8192, bs);    /* sane upper bound */
    TEST_ASSERT_EQUAL_UINT(0, bs & (bs - 1));    /* power of two */
}

/* a large buffer that spans several dc-zva blocks zeroes fully (exercises the aligned
 * middle path once GREEN; the byte loop already passes -> a regression guard). */
static void test_wipe_large_buffer(void) {
    unsigned char buf[1024];
    memset(buf, 0xFF, sizeof(buf));
    purge_wipe(buf, sizeof(buf));
    for (size_t i = 0; i < sizeof(buf); i++) {
        TEST_ASSERT_EQUAL_HEX8(0x00, buf[i]);
    }
}

void run_wipe_tests(void) {
    RUN_TEST(test_wipe_zeros_buffer);
    RUN_TEST(test_wipe_zero_len_is_noop);
    RUN_TEST(test_wipe_partial_leaves_tail);
    RUN_TEST(test_zva_blocksize_sane);
    RUN_TEST(test_wipe_large_buffer);
}
