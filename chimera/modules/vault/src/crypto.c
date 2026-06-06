/* VAULT crypto (§3, §5) — XChaCha20-Poly1305 AEAD + Argon2id KDF + secure memory,
 * via libsodium. Fail-closed throughout; the key never lingers in ordinary memory.
 *
 * Security notes:
 *   - derive feeds Argon2id a transient (master_secret || policy_hash) buffer held
 *     in sodium-secure memory and wiped immediately after — the raw master secret
 *     must not survive the call or reach swap / a core dump (VAULT's no-leak thesis).
 *   - open verifies the Poly1305 tag BEFORE releasing any plaintext; on any failure
 *     it returns false and zeroes pt_out (defensive — libsodium already writes
 *     nothing on auth failure).
 *   - seal draws a fresh random 192-bit nonce per call (XChaCha20 nonce-misuse
 *     resistance). */
#include "crypto.h"

#include <string.h>

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
    /* Argon2id password = master_secret || policy_hash (binds the key to the policy).
     * The combined buffer holds the raw master secret, so it lives in sodium-secure
     * memory and is wiped the moment derivation finishes. */
    const size_t combined_len = master_len + 32;
    uint8_t *combined = sodium_malloc(combined_len);
    if (combined == NULL) {
        return false;
    }
    memcpy(combined, master_secret, master_len);
    memcpy(combined + master_len, policy_hash, 32);

    const int rc = crypto_pwhash(
        key_out, VAULT_KEY_BYTES, (const char *)combined, combined_len, salt,
        crypto_pwhash_OPSLIMIT_MODERATE, crypto_pwhash_MEMLIMIT_MODERATE,
        crypto_pwhash_ALG_ARGON2ID13);

    sodium_free(combined); /* zeroes the master-secret-bearing buffer */
    return rc == 0;
}

bool vault_crypto_seal(const uint8_t key[VAULT_KEY_BYTES], const uint8_t *plaintext,
                       size_t plaintext_len, uint8_t nonce_out[VAULT_NONCE_BYTES],
                       uint8_t *ct_out, size_t *ct_len_out) {
    randombytes_buf(nonce_out, VAULT_NONCE_BYTES); /* fresh 192-bit nonce per seal */
    unsigned long long ct_len = 0;
    const int rc = crypto_aead_xchacha20poly1305_ietf_encrypt(
        ct_out, &ct_len, plaintext, plaintext_len, NULL, 0, NULL, nonce_out, key);
    if (rc != 0) {
        return false;
    }
    if (ct_len_out != NULL) {
        *ct_len_out = (size_t)ct_len;
    }
    return true;
}

bool vault_crypto_open(const uint8_t key[VAULT_KEY_BYTES],
                       const uint8_t nonce[VAULT_NONCE_BYTES], const uint8_t *ct,
                       size_t ct_len, uint8_t *pt_out, size_t *pt_len_out) {
    unsigned long long pt_len = 0;
    const int rc = crypto_aead_xchacha20poly1305_ietf_decrypt(
        pt_out, &pt_len, NULL, ct, ct_len, NULL, 0, nonce, key);
    if (rc != 0) {
        /* Auth failed (wrong key / tamper): libsodium wrote nothing; zero pt_out
         * defensively so no caller can read a partial plaintext. */
        if (ct_len > VAULT_TAG_BYTES) {
            sodium_memzero(pt_out, ct_len - VAULT_TAG_BYTES);
        }
        return false;
    }
    if (pt_len_out != NULL) {
        *pt_len_out = (size_t)pt_len;
    }
    return true;
}

void *vault_secure_alloc(size_t len) {
    return sodium_malloc(len);
}

void vault_secure_free(void *p) {
    sodium_free(p); /* NULL-safe; zeroes the region */
}
