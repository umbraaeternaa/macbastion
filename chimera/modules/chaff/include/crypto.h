/* Fernet (AES-128-CBC + HMAC-SHA256) for profile/state at rest (§5.1, D5). */
#ifndef CHAFF_CRYPTO_H
#define CHAFF_CRYPTO_H

#include <stddef.h>
#include <stdint.h>

#include "chaff.h"

#define FERNET_KEY_LEN 32 /* 16 signing + 16 encryption */

/* Encrypt plaintext into a Fernet token (base64url, NUL-terminated). On
 * CHAFF_OK, *out_token is owned by the caller (free()). Non-deterministic
 * (random IV + timestamp). */
chaff_result_t fernet_encrypt(const uint8_t key[FERNET_KEY_LEN], const uint8_t *plaintext,
                              size_t len, char **out_token);

/* Decrypt + verify a Fernet token. On CHAFF_OK, *out is owned plaintext of
 * *out_len bytes. CHAFF_ERR_CRYPTO on a bad key or a tampered token (HMAC). */
chaff_result_t fernet_decrypt(const uint8_t key[FERNET_KEY_LEN], const char *token,
                              uint8_t **out, size_t *out_len);

#endif /* CHAFF_CRYPTO_H */
