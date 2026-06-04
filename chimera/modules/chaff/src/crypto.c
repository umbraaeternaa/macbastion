/* crypto — STUB (RED-B). Real Fernet (openssl AES-128-CBC + HMAC) lands in GREEN. */
#include "crypto.h"

chaff_result_t fernet_encrypt(const uint8_t key[FERNET_KEY_LEN], const uint8_t *plaintext,
                              size_t len, char **out_token) {
    (void)key;
    (void)plaintext;
    (void)len;
    if (out_token) {
        *out_token = NULL;
    }
    return CHAFF_ERR_CRYPTO; /* TODO(green): build + sign Fernet token */
}

chaff_result_t fernet_decrypt(const uint8_t key[FERNET_KEY_LEN], const char *token,
                              uint8_t **out, size_t *out_len) {
    (void)key;
    (void)token;
    if (out) {
        *out = NULL;
    }
    if (out_len) {
        *out_len = 0;
    }
    return CHAFF_ERR_CRYPTO; /* TODO(green): verify HMAC + decrypt */
}
