/* crypto — Fernet (AES-128-CBC + HMAC-SHA256) via OpenSSL (§5.1, D5).
 *
 * Token = base64url( 0x80 | timestamp(8) | IV(16) | ciphertext | HMAC(32) ).
 * Key = signing_key (first 16 bytes) || encryption_key (last 16 bytes).
 * HMAC is computed over everything before it; verified in constant time. */
#include "crypto.h"

#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <openssl/hmac.h>
#include <openssl/rand.h>

#define FERNET_VERSION 0x80
#define IV_LEN 16
#define TS_LEN 8
#define HMAC_LEN 32
#define HEADER_LEN (1 + TS_LEN + IV_LEN)

static const char B64URL[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

static char *b64url_encode(const uint8_t *in, size_t len) {
    size_t olen = 4 * ((len + 2) / 3);
    char *out = malloc(olen + 1);
    if (!out) {
        return NULL;
    }
    size_t o = 0;
    for (size_t i = 0; i < len; i += 3) {
        size_t rem = len - i;
        uint32_t trip = (uint32_t)in[i] << 16;
        if (rem > 1) {
            trip |= (uint32_t)in[i + 1] << 8;
        }
        if (rem > 2) {
            trip |= (uint32_t)in[i + 2];
        }
        out[o++] = B64URL[(trip >> 18) & 0x3f];
        out[o++] = B64URL[(trip >> 12) & 0x3f];
        out[o++] = (rem > 1) ? B64URL[(trip >> 6) & 0x3f] : '=';
        out[o++] = (rem > 2) ? B64URL[trip & 0x3f] : '=';
    }
    out[o] = '\0';
    return out;
}

static int b64val(char c) {
    if (c >= 'A' && c <= 'Z') {
        return c - 'A';
    }
    if (c >= 'a' && c <= 'z') {
        return c - 'a' + 26;
    }
    if (c >= '0' && c <= '9') {
        return c - '0' + 52;
    }
    if (c == '-') {
        return 62;
    }
    if (c == '_') {
        return 63;
    }
    return -1;
}

static uint8_t *b64url_decode(const char *in, size_t *out_len) {
    size_t len = strlen(in);
    while (len > 0 && in[len - 1] == '=') {
        len--;
    }
    uint8_t *out = malloc(len / 4 * 3 + 3);
    if (!out) {
        return NULL;
    }
    size_t o = 0;
    uint32_t buf = 0;
    int bits = 0;
    for (size_t i = 0; i < len; i++) {
        int v = b64val(in[i]);
        if (v < 0) {
            free(out);
            return NULL;
        }
        buf = (buf << 6) | (uint32_t)v;
        bits += 6;
        if (bits >= 8) {
            bits -= 8;
            out[o++] = (uint8_t)((buf >> bits) & 0xff);
        }
    }
    *out_len = o;
    return out;
}

chaff_result_t fernet_encrypt(const uint8_t key[FERNET_KEY_LEN], const uint8_t *plaintext,
                              size_t len, char **out_token) {
    if (!key || !out_token || (!plaintext && len > 0)) {
        return CHAFF_ERR;
    }
    *out_token = NULL;
    const uint8_t *sign_key = key;
    const uint8_t *enc_key = key + 16;

    uint8_t iv[IV_LEN];
    if (RAND_bytes(iv, IV_LEN) != 1) {
        return CHAFF_ERR_CRYPTO;
    }

    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    uint8_t *ct = malloc(len + IV_LEN);
    uint8_t *msg = NULL;
    chaff_result_t res = CHAFF_ERR_CRYPTO;
    if (!ctx || !ct) {
        goto done;
    }

    int ct_len = 0, tmp = 0;
    if (EVP_EncryptInit_ex(ctx, EVP_aes_128_cbc(), NULL, enc_key, iv) != 1 ||
        EVP_EncryptUpdate(ctx, ct, &ct_len, plaintext ? plaintext : (const uint8_t *)"",
                          (int)len) != 1 ||
        EVP_EncryptFinal_ex(ctx, ct + ct_len, &tmp) != 1) {
        goto done;
    }
    ct_len += tmp;

    size_t body = HEADER_LEN + (size_t)ct_len;
    msg = malloc(body + HMAC_LEN);
    if (!msg) {
        goto done;
    }
    uint64_t ts = (uint64_t)time(NULL);
    size_t p = 0;
    msg[p++] = FERNET_VERSION;
    for (int i = 7; i >= 0; i--) {
        msg[p++] = (uint8_t)((ts >> (i * 8)) & 0xff);
    }
    memcpy(msg + p, iv, IV_LEN);
    p += IV_LEN;
    memcpy(msg + p, ct, (size_t)ct_len);
    p += (size_t)ct_len;

    unsigned int hlen = 0;
    if (!HMAC(EVP_sha256(), sign_key, 16, msg, p, msg + p, &hlen) || hlen != HMAC_LEN) {
        goto done;
    }
    p += HMAC_LEN;

    char *tok = b64url_encode(msg, p);
    if (tok) {
        *out_token = tok;
        res = CHAFF_OK;
    }

done:
    if (ctx) {
        EVP_CIPHER_CTX_free(ctx);
    }
    free(ct);
    free(msg);
    return res;
}

chaff_result_t fernet_decrypt(const uint8_t key[FERNET_KEY_LEN], const char *token, uint8_t **out,
                              size_t *out_len) {
    if (!key || !token || !out || !out_len) {
        return CHAFF_ERR;
    }
    *out = NULL;
    *out_len = 0;
    const uint8_t *sign_key = key;
    const uint8_t *enc_key = key + 16;

    size_t mlen = 0;
    uint8_t *msg = b64url_decode(token, &mlen);
    if (!msg) {
        return CHAFF_ERR_CRYPTO;
    }

    EVP_CIPHER_CTX *ctx = NULL;
    uint8_t *pt = NULL;
    chaff_result_t res = CHAFF_ERR_CRYPTO;

    if (mlen < HEADER_LEN + HMAC_LEN || msg[0] != FERNET_VERSION) {
        goto done;
    }
    size_t body = mlen - HMAC_LEN;

    uint8_t mac[HMAC_LEN];
    unsigned int hlen = 0;
    if (!HMAC(EVP_sha256(), sign_key, 16, msg, body, mac, &hlen) || hlen != HMAC_LEN) {
        goto done;
    }
    if (CRYPTO_memcmp(mac, msg + body, HMAC_LEN) != 0) {
        goto done; /* wrong key or tampered token */
    }

    const uint8_t *iv = msg + 1 + TS_LEN;
    const uint8_t *ct = msg + HEADER_LEN;
    size_t ct_len = body - HEADER_LEN;

    ctx = EVP_CIPHER_CTX_new();
    pt = malloc(ct_len + IV_LEN + 1);
    if (!ctx || !pt) {
        goto done;
    }
    int pl = 0, tmp = 0;
    if (EVP_DecryptInit_ex(ctx, EVP_aes_128_cbc(), NULL, enc_key, iv) != 1 ||
        EVP_DecryptUpdate(ctx, pt, &pl, ct, (int)ct_len) != 1 ||
        EVP_DecryptFinal_ex(ctx, pt + pl, &tmp) != 1) {
        goto done; /* bad padding */
    }
    pl += tmp;
    *out = pt;
    *out_len = (size_t)pl;
    pt = NULL; /* ownership transferred */
    res = CHAFF_OK;

done:
    if (ctx) {
        EVP_CIPHER_CTX_free(ctx);
    }
    free(pt);
    free(msg);
    return res;
}
