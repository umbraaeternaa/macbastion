/* RED-B contract for Fernet crypto. Fails against the stubs until GREEN. */
#include "unity.h"

#include <stdlib.h>
#include <string.h>

#include "crypto.h"

/* Hardcoded keys for deterministic round-trip tests (Sub-D4=A). */
static const uint8_t KEY[FERNET_KEY_LEN] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
    0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f};
static const uint8_t OTHER_KEY[FERNET_KEY_LEN] = {
    0xff, 0xfe, 0xfd, 0xfc, 0xfb, 0xfa, 0xf9, 0xf8, 0xf7, 0xf6, 0xf5, 0xf4, 0xf3, 0xf2, 0xf1, 0xf0,
    0xef, 0xee, 0xed, 0xec, 0xeb, 0xea, 0xe9, 0xe8, 0xe7, 0xe6, 0xe5, 0xe4, 0xe3, 0xe2, 0xe1, 0xe0};

static void test_round_trip(void) {
    const char *msg = "hello chaff";
    char *token = NULL;
    TEST_ASSERT_EQUAL_INT(CHAFF_OK,
                          fernet_encrypt(KEY, (const uint8_t *)msg, strlen(msg), &token));
    TEST_ASSERT_NOT_NULL(token);
    uint8_t *out = NULL;
    size_t out_len = 0;
    TEST_ASSERT_EQUAL_INT(CHAFF_OK, fernet_decrypt(KEY, token, &out, &out_len));
    TEST_ASSERT_EQUAL_size_t(strlen(msg), out_len);
    TEST_ASSERT_EQUAL_MEMORY(msg, out, out_len);
    free(token);
    free(out);
}

static void test_wrong_key_fails(void) {
    const char *msg = "secret";
    char *token = NULL;
    TEST_ASSERT_EQUAL_INT(CHAFF_OK,
                          fernet_encrypt(KEY, (const uint8_t *)msg, strlen(msg), &token));
    uint8_t *out = NULL;
    size_t out_len = 0;
    TEST_ASSERT_EQUAL_INT(CHAFF_ERR_CRYPTO, fernet_decrypt(OTHER_KEY, token, &out, &out_len));
    free(token);
}

static void test_tampered_token_fails(void) {
    const char *msg = "integrity";
    char *token = NULL;
    TEST_ASSERT_EQUAL_INT(CHAFF_OK,
                          fernet_encrypt(KEY, (const uint8_t *)msg, strlen(msg), &token));
    TEST_ASSERT_NOT_NULL(token);
    token[0] = (token[0] == 'A') ? 'B' : 'A'; /* flip a byte */
    uint8_t *out = NULL;
    size_t out_len = 0;
    TEST_ASSERT_EQUAL_INT(CHAFF_ERR_CRYPTO, fernet_decrypt(KEY, token, &out, &out_len));
    free(token);
}

static void test_nondeterministic_iv(void) {
    const char *msg = "same plaintext";
    char *t1 = NULL, *t2 = NULL;
    TEST_ASSERT_EQUAL_INT(CHAFF_OK, fernet_encrypt(KEY, (const uint8_t *)msg, strlen(msg), &t1));
    TEST_ASSERT_EQUAL_INT(CHAFF_OK, fernet_encrypt(KEY, (const uint8_t *)msg, strlen(msg), &t2));
    TEST_ASSERT_NOT_NULL(t1);
    TEST_ASSERT_NOT_NULL(t2);
    TEST_ASSERT_NOT_EQUAL(0, strcmp(t1, t2)); /* random IV -> different tokens */
    free(t1);
    free(t2);
}

static void test_empty_plaintext(void) {
    char *token = NULL;
    TEST_ASSERT_EQUAL_INT(CHAFF_OK, fernet_encrypt(KEY, (const uint8_t *)"", 0, &token));
    uint8_t *out = NULL;
    size_t out_len = 1;
    TEST_ASSERT_EQUAL_INT(CHAFF_OK, fernet_decrypt(KEY, token, &out, &out_len));
    TEST_ASSERT_EQUAL_size_t(0, out_len);
    free(token);
    free(out);
}

static void test_binary_data(void) {
    const uint8_t blob[] = {0x00, 0xff, 0x10, 0x00, 0x7f, 0x80};
    char *token = NULL;
    TEST_ASSERT_EQUAL_INT(CHAFF_OK, fernet_encrypt(KEY, blob, sizeof(blob), &token));
    uint8_t *out = NULL;
    size_t out_len = 0;
    TEST_ASSERT_EQUAL_INT(CHAFF_OK, fernet_decrypt(KEY, token, &out, &out_len));
    TEST_ASSERT_EQUAL_size_t(sizeof(blob), out_len);
    TEST_ASSERT_EQUAL_MEMORY(blob, out, sizeof(blob));
    free(token);
    free(out);
}

void run_crypto_tests(void) {
    RUN_TEST(test_round_trip);
    RUN_TEST(test_wrong_key_fails);
    RUN_TEST(test_tampered_token_fails);
    RUN_TEST(test_nondeterministic_iv);
    RUN_TEST(test_empty_plaintext);
    RUN_TEST(test_binary_data);
}
