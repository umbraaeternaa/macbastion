/* Contract for the crypto engine (§3, §5): Argon2id derive + XChaCha20-Poly1305
 * seal/open + secure memory. RED: derive/seal/open/secure_alloc are stubs (false /
 * NULL), so every test fails; vault_crypto_init is real (returns true). Hermetic —
 * the master secret is injected (no Keychain); seal/open use a fixed key to isolate
 * from derive. */
#include "unity.h"

#include <string.h>

#include "crypto.h"

/* A fixed 32-byte key for the AEAD tests (isolates them from derive). */
static const uint8_t KEY[VAULT_KEY_BYTES] = {
    1,  2,  3,  4,  5,  6,  7,  8,  9,  10, 11, 12, 13, 14, 15, 16,
    17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32,
};
static const uint8_t OTHER_KEY[VAULT_KEY_BYTES] = {
    32, 31, 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 17,
    16, 15, 14, 13, 12, 11, 10, 9,  8,  7,  6,  5,  4,  3,  2,  1,
};

/* Derive is deterministic for fixed inputs (STABLE salt -> same key, so stored
 * ciphertext stays decryptable — catch A). */
static void test_crypto_derive_determinism(void) {
    TEST_ASSERT_TRUE(vault_crypto_init());
    const uint8_t ms[] = "master-secret-injected";
    uint8_t ph[32];
    memset(ph, 0xAB, sizeof ph);
    uint8_t salt[VAULT_SALT_BYTES];
    memset(salt, 0x11, sizeof salt);
    uint8_t k1[VAULT_KEY_BYTES], k2[VAULT_KEY_BYTES];
    TEST_ASSERT_TRUE(vault_crypto_derive(ms, sizeof ms - 1, ph, salt, k1));
    TEST_ASSERT_TRUE(vault_crypto_derive(ms, sizeof ms - 1, ph, salt, k2));
    TEST_ASSERT_EQUAL_MEMORY(k1, k2, VAULT_KEY_BYTES);
}

/* A different salt yields a different key — proves the salt is actually mixed in. */
static void test_crypto_derive_salt_sensitivity(void) {
    TEST_ASSERT_TRUE(vault_crypto_init());
    const uint8_t ms[] = "master-secret-injected";
    uint8_t ph[32];
    memset(ph, 0xAB, sizeof ph);
    uint8_t salt_a[VAULT_SALT_BYTES], salt_b[VAULT_SALT_BYTES];
    memset(salt_a, 0x11, sizeof salt_a);
    memset(salt_b, 0x22, sizeof salt_b);
    uint8_t ka[VAULT_KEY_BYTES], kb[VAULT_KEY_BYTES];
    TEST_ASSERT_TRUE(vault_crypto_derive(ms, sizeof ms - 1, ph, salt_a, ka));
    TEST_ASSERT_TRUE(vault_crypto_derive(ms, sizeof ms - 1, ph, salt_b, kb));
    TEST_ASSERT_TRUE(memcmp(ka, kb, VAULT_KEY_BYTES) != 0);
}

/* Seal then open round-trips the plaintext. */
static void test_crypto_seal_open_roundtrip(void) {
    TEST_ASSERT_TRUE(vault_crypto_init());
    const uint8_t pt[] = "the vault's secret payload";
    const size_t ptlen = sizeof pt - 1;
    uint8_t nonce[VAULT_NONCE_BYTES];
    uint8_t ct[64];
    size_t ctlen = 0;
    TEST_ASSERT_TRUE(vault_crypto_seal(KEY, pt, ptlen, nonce, ct, &ctlen));
    TEST_ASSERT_EQUAL_size_t(ptlen + VAULT_TAG_BYTES, ctlen);
    uint8_t out[64];
    size_t outlen = 0;
    TEST_ASSERT_TRUE(vault_crypto_open(KEY, nonce, ct, ctlen, out, &outlen));
    TEST_ASSERT_EQUAL_size_t(ptlen, outlen);
    TEST_ASSERT_EQUAL_MEMORY(pt, out, ptlen);
}

/* Tampering with the ciphertext makes open fail — and leaks NO plaintext. */
static void test_crypto_tamper_detected(void) {
    TEST_ASSERT_TRUE(vault_crypto_init());
    const uint8_t pt[] = "tamper me";
    const size_t ptlen = sizeof pt - 1;
    uint8_t nonce[VAULT_NONCE_BYTES];
    uint8_t ct[64];
    size_t ctlen = 0;
    TEST_ASSERT_TRUE(vault_crypto_seal(KEY, pt, ptlen, nonce, ct, &ctlen));
    ct[0] ^= 0xFF; /* flip a ciphertext byte */
    uint8_t out[64];
    memset(out, 0xAA, sizeof out); /* sentinel */
    size_t outlen = 0;
    TEST_ASSERT_FALSE(vault_crypto_open(KEY, nonce, ct, ctlen, out, &outlen));
    /* tamper -> open() returns false AND wipes pt_out (defensive, design-pass nuance 3).
     * The invariant is "no plaintext leak", not a specific sentinel byte — assert the
     * buffer does NOT contain the plaintext (holds whether wiped to 0 or left untouched). */
    TEST_ASSERT_TRUE(memcmp(out, pt, ptlen) != 0);
}

/* A wrong key makes open fail (AEAD authentication). */
static void test_crypto_wrong_key_fails(void) {
    TEST_ASSERT_TRUE(vault_crypto_init());
    const uint8_t pt[] = "secret";
    const size_t ptlen = sizeof pt - 1;
    uint8_t nonce[VAULT_NONCE_BYTES];
    uint8_t ct[64];
    size_t ctlen = 0;
    TEST_ASSERT_TRUE(vault_crypto_seal(KEY, pt, ptlen, nonce, ct, &ctlen));
    uint8_t out[64];
    size_t outlen = 0;
    TEST_ASSERT_FALSE(vault_crypto_open(OTHER_KEY, nonce, ct, ctlen, out, &outlen));
}

/* Two seals of the same plaintext use different nonces (XChaCha20 misuse-resistance
 * — catch B). Distinct nonces also yield distinct ciphertext. */
static void test_crypto_nonce_uniqueness(void) {
    TEST_ASSERT_TRUE(vault_crypto_init());
    const uint8_t pt[] = "same plaintext";
    const size_t ptlen = sizeof pt - 1;
    uint8_t n1[VAULT_NONCE_BYTES], n2[VAULT_NONCE_BYTES];
    uint8_t c1[64], c2[64];
    size_t l1 = 0, l2 = 0;
    TEST_ASSERT_TRUE(vault_crypto_seal(KEY, pt, ptlen, n1, c1, &l1));
    TEST_ASSERT_TRUE(vault_crypto_seal(KEY, pt, ptlen, n2, c2, &l2));
    TEST_ASSERT_TRUE(memcmp(n1, n2, VAULT_NONCE_BYTES) != 0);
    TEST_ASSERT_TRUE(memcmp(c1, c2, l1) != 0);
}

/* Secure memory: alloc returns usable memory; free does not crash. */
static void test_crypto_secure_alloc_roundtrip(void) {
    TEST_ASSERT_TRUE(vault_crypto_init());
    uint8_t *p = vault_secure_alloc(64);
    TEST_ASSERT_NOT_NULL(p);
    memset(p, 0x5A, 64);
    TEST_ASSERT_EQUAL_UINT8(0x5A, p[0]);
    vault_secure_free(p);
}

void run_crypto_tests(void) {
    RUN_TEST(test_crypto_derive_determinism);
    RUN_TEST(test_crypto_derive_salt_sensitivity);
    RUN_TEST(test_crypto_seal_open_roundtrip);
    RUN_TEST(test_crypto_tamper_detected);
    RUN_TEST(test_crypto_wrong_key_fails);
    RUN_TEST(test_crypto_nonce_uniqueness);
    RUN_TEST(test_crypto_secure_alloc_roundtrip);
}
