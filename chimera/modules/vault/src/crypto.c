/* VAULT crypto — RED stubs (XChaCha20-Poly1305 + Argon2id + secure memory).
 * vault_crypto_init is real (needed to link libsodium and run the suite); derive/
 * seal/open/secure_alloc are stubs that fail, so the crypto tests are red. GREEN
 * wires the libsodium calls. */
#include "crypto.h"

#include <sodium.h>

/* Compile-time: our plain #defines must equal the libsodium constants. */
_Static_assert(VAULT_KEY_BYTES == crypto_aead_xchacha20poly1305_ietf_KEYBYTES,
               "key size mismatch");
_Static_assert(VAULT_NONCE_BYTES == crypto_aead_xchacha20poly1305_ietf_NPUBBYTES,
               "nonce size mismatch");
_Static_assert(VAULT_TAG_BYTES == crypto_aead_xchacha20poly1305_ietf_ABYTES,
               "tag size mismatch");
_Static_assert(VAULT_SALT_BYTES == crypto_pwhash_SALTBYTES, "salt size mismatch");

bool vault_crypto_init(void) {
    return sodium_init() >= 0;
}

bool vault_crypto_derive(const uint8_t *master_secret, size_t master_len,
                         const uint8_t policy_hash[32],
                         const uint8_t salt[VAULT_SALT_BYTES],
                         uint8_t key_out[VAULT_KEY_BYTES]) {
    (void)master_secret;
    (void)master_len;
    (void)policy_hash;
    (void)salt;
    (void)key_out;
    return false; /* RED */
}

bool vault_crypto_seal(const uint8_t key[VAULT_KEY_BYTES], const uint8_t *plaintext,
                       size_t plaintext_len, uint8_t nonce_out[VAULT_NONCE_BYTES],
                       uint8_t *ct_out, size_t *ct_len_out) {
    (void)key;
    (void)plaintext;
    (void)plaintext_len;
    (void)nonce_out;
    (void)ct_out;
    (void)ct_len_out;
    return false; /* RED */
}

bool vault_crypto_open(const uint8_t key[VAULT_KEY_BYTES],
                       const uint8_t nonce[VAULT_NONCE_BYTES], const uint8_t *ct,
                       size_t ct_len, uint8_t *pt_out, size_t *pt_len_out) {
    (void)key;
    (void)nonce;
    (void)ct;
    (void)ct_len;
    (void)pt_out;
    (void)pt_len_out;
    return false; /* RED */
}

void *vault_secure_alloc(size_t len) {
    (void)len;
    return NULL; /* RED */
}

void vault_secure_free(void *p) {
    (void)p; /* RED */
}
