/* VAULT per-vault master secret in the login Keychain (VD-3). The real SecItem backend is
 * manual-tier; the seam lets tests inject an in-memory store. RED: load_or_create returns -1
 * until GREEN (no faked secret, MANIFESTO §4). */
#include "keychain.h"

#include <stdlib.h>
#include <string.h>

#include <CoreFoundation/CoreFoundation.h>
#include <Security/Security.h>

#define KC_SERVICE CFSTR("com.umbra.chimera")

/* Real backend: a generic-password item, service "com.umbra.chimera", account = vault_id. */
static int keychain_load_real(const char *vault_id, unsigned char *out) {
    CFStringRef acct = CFStringCreateWithCString(NULL, vault_id, kCFStringEncodingUTF8);
    if (acct == NULL) {
        return -1;
    }
    const void *keys[] = {kSecClass, kSecAttrService, kSecAttrAccount, kSecReturnData,
                          kSecMatchLimit};
    const void *vals[] = {kSecClassGenericPassword, KC_SERVICE, acct, kCFBooleanTrue,
                          kSecMatchLimitOne};
    CFDictionaryRef q = CFDictionaryCreate(NULL, keys, vals, 5, &kCFTypeDictionaryKeyCallBacks,
                                           &kCFTypeDictionaryValueCallBacks);
    CFTypeRef data = NULL;
    OSStatus st = q ? SecItemCopyMatching(q, &data) : errSecParam;
    if (q) {
        CFRelease(q);
    }
    CFRelease(acct);
    if (st == errSecItemNotFound) {
        return 0;
    }
    if (st != errSecSuccess || data == NULL) {
        if (data) {
            CFRelease(data);
        }
        return -1;
    }
    CFDataRef d = (CFDataRef)data;
    int rc = -1;
    if (CFDataGetLength(d) == VAULT_MASTER_SECRET_LEN) {
        memcpy(out, CFDataGetBytePtr(d), VAULT_MASTER_SECRET_LEN);
        rc = 1;
    }
    CFRelease(d);
    return rc;
}

static int keychain_store_real(const char *vault_id, const unsigned char *secret) {
    CFStringRef acct = CFStringCreateWithCString(NULL, vault_id, kCFStringEncodingUTF8);
    CFDataRef data = CFDataCreate(NULL, secret, VAULT_MASTER_SECRET_LEN);
    if (acct == NULL || data == NULL) {
        if (acct) {
            CFRelease(acct);
        }
        if (data) {
            CFRelease(data);
        }
        return -1;
    }
    const void *keys[] = {kSecClass, kSecAttrService, kSecAttrAccount, kSecValueData};
    const void *vals[] = {kSecClassGenericPassword, KC_SERVICE, acct, data};
    CFDictionaryRef q = CFDictionaryCreate(NULL, keys, vals, 4, &kCFTypeDictionaryKeyCallBacks,
                                           &kCFTypeDictionaryValueCallBacks);
    OSStatus st = q ? SecItemAdd(q, NULL) : errSecParam;
    if (q) {
        CFRelease(q);
    }
    CFRelease(acct);
    CFRelease(data);
    return (st == errSecSuccess) ? 0 : -1;
}

static int keychain_delete_real(const char *vault_id) {
    CFStringRef acct = CFStringCreateWithCString(NULL, vault_id, kCFStringEncodingUTF8);
    if (acct == NULL) {
        return -1;
    }
    const void *keys[] = {kSecClass, kSecAttrService, kSecAttrAccount};
    const void *vals[] = {kSecClassGenericPassword, KC_SERVICE, acct};
    CFDictionaryRef q = CFDictionaryCreate(NULL, keys, vals, 3, &kCFTypeDictionaryKeyCallBacks,
                                           &kCFTypeDictionaryValueCallBacks);
    OSStatus st = q ? SecItemDelete(q) : errSecParam;
    if (q) {
        CFRelease(q);
    }
    CFRelease(acct);
    return (st == errSecSuccess || st == errSecItemNotFound) ? 0 : -1;
}

static vault_keychain_backend_t g_backend = {keychain_load_real, keychain_store_real,
                                             keychain_delete_real};

vault_keychain_backend_t vault_keychain_set_backend(vault_keychain_backend_t b) {
    vault_keychain_backend_t prev = g_backend;
    g_backend.load = b.load ? b.load : keychain_load_real;
    g_backend.store = b.store ? b.store : keychain_store_real;
    g_backend.del = b.del ? b.del : keychain_delete_real;
    return prev;
}

int vault_keychain_delete(const char *vault_id) {
    if (vault_id == NULL) {
        return -1;
    }
    return g_backend.del(vault_id);
}

int vault_keychain_load_or_create(const char *vault_id, unsigned char *out) {
    if (vault_id == NULL || out == NULL) {
        return -1;
    }
    int r = g_backend.load(vault_id, out);
    if (r == 1) {
        return 0; /* found */
    }
    if (r < 0) {
        return -1; /* backend error */
    }
    /* absent -> generate a fresh 32-byte master secret + store it */
    arc4random_buf(out, VAULT_MASTER_SECRET_LEN);
    if (g_backend.store(vault_id, out) != 0) {
        return -1;
    }
    return 0;
}
