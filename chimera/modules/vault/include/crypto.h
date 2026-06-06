/* VAULT crypto (§3, §5) — XChaCha20-Poly1305 AEAD + Argon2id KDF + secure memory,
 * via libsodium. The key NEVER exists unless a policy ALLOWs (state-gated); this
 * layer is the mechanical engine (derive / seal / open) — the gating orchestration
 * (eval -> derive) and the real Keychain/Enclave master secret are later slices.
 * Here the master secret is supplied by the caller (hermetic / injected).
 *
 * Sizes are plain #defines (so this header needs no <sodium.h>); crypto.c asserts
 * they equal the libsodium constants at compile time. */
#ifndef VAULT_CRYPTO_H
#define VAULT_CRYPTO_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define VAULT_KEY_BYTES 32   /* crypto_aead_xchacha20poly1305_ietf_KEYBYTES */
#define VAULT_NONCE_BYTES 24 /* ..._NPUBBYTES — 192-bit, nonce-misuse-resistant */
#define VAULT_TAG_BYTES 16   /* ..._ABYTES — Poly1305 tag */
#define VAULT_SALT_BYTES 16  /* crypto_pwhash_SALTBYTES */

/* Initialize libsodium. Call once before any other crypto call. Idempotent;
 * returns false only on a libsodium init failure. */
bool vault_crypto_init(void);

/* Derive a 32-byte vault key via Argon2id (MODERATE preset) from the master secret,
 * the 32-byte policy hash, and the per-vault salt. DETERMINISTIC for fixed inputs —
 * a STABLE salt yields the same key, so stored ciphertext stays decryptable (the
 * salt rotates only on re-encryption). Returns false on failure (e.g. the
 * memory-hard KDF cannot get its memory). key_out is VAULT_KEY_BYTES. */
bool vault_crypto_derive(const uint8_t *master_secret, size_t master_len,
                         const uint8_t policy_hash[32],
                         const uint8_t salt[VAULT_SALT_BYTES],
                         uint8_t key_out[VAULT_KEY_BYTES]);

/* Seal plaintext with XChaCha20-Poly1305 under `key`, generating a FRESH random
 * 192-bit nonce into nonce_out. ct_out must hold plaintext_len + VAULT_TAG_BYTES
 * (the tag is appended); *ct_len_out receives the total. Returns false on failure. */
bool vault_crypto_seal(const uint8_t key[VAULT_KEY_BYTES], const uint8_t *plaintext,
                       size_t plaintext_len, uint8_t nonce_out[VAULT_NONCE_BYTES],
                       uint8_t *ct_out, size_t *ct_len_out);

/* Open (decrypt + verify). The AEAD verifies the Poly1305 tag BEFORE releasing any
 * plaintext: a wrong key or ANY tampering returns false and writes nothing usable to
 * pt_out (fail-closed — no partial-plaintext leak). pt_out must hold
 * ct_len - VAULT_TAG_BYTES; *pt_len_out receives the plaintext length on success. */
bool vault_crypto_open(const uint8_t key[VAULT_KEY_BYTES],
                       const uint8_t nonce[VAULT_NONCE_BYTES], const uint8_t *ct,
                       size_t ct_len, uint8_t *pt_out, size_t *pt_len_out);

/* Secure memory: sodium_malloc (guard pages + canary + mlock) / sodium_free (zeroes
 * on free). For keys and plaintext that must never reach swap or a core dump.
 * vault_secure_alloc returns NULL on failure; vault_secure_free is NULL-safe. */
void *vault_secure_alloc(size_t len);
void vault_secure_free(void *p);

#endif /* VAULT_CRYPTO_H */
