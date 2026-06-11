/* VAULT keychain master-secret contract (VD-3). The real SecItem path is manual-tier; these
 * hermetic tests use an in-memory backend that the runner's setUp installs before EVERY test, so
 * no test ever touches the real login Keychain. RED: vault_keychain_load_or_create returns -1. */
#include "unity.h"

#include <stdio.h>
#include <string.h>

#include "keychain.h"

#define MEM_MAX 8
static struct {
    char vault_id[64];
    unsigned char secret[VAULT_MASTER_SECRET_LEN];
    int present;
} g_mem[MEM_MAX];

static int mem_load(const char *vault_id, unsigned char *out) {
    for (int i = 0; i < MEM_MAX; i++) {
        if (g_mem[i].present && strcmp(g_mem[i].vault_id, vault_id) == 0) {
            memcpy(out, g_mem[i].secret, VAULT_MASTER_SECRET_LEN);
            return 1;
        }
    }
    return 0;
}

static int mem_store(const char *vault_id, const unsigned char *secret) {
    for (int i = 0; i < MEM_MAX; i++) {
        if (!g_mem[i].present) {
            snprintf(g_mem[i].vault_id, sizeof(g_mem[i].vault_id), "%s", vault_id);
            memcpy(g_mem[i].secret, secret, VAULT_MASTER_SECRET_LEN);
            g_mem[i].present = 1;
            return 0;
        }
    }
    return -1;
}

static int mem_del(const char *vault_id) {
    for (int i = 0; i < MEM_MAX; i++) {
        if (g_mem[i].present && strcmp(g_mem[i].vault_id, vault_id) == 0) {
            memset(&g_mem[i], 0, sizeof(g_mem[i]));
            return 0;
        }
    }
    return 0; /* already absent is success */
}

/* Installed by the runner's setUp: reset the store + swap in the in-memory backend. */
void vault_test_install_mem_keychain(void) {
    memset(g_mem, 0, sizeof(g_mem));
    vault_keychain_backend_t b = {mem_load, mem_store, mem_del};
    vault_keychain_set_backend(b);
}

/* How many master secrets the in-memory keychain currently holds (for wiring assertions). */
int vault_test_keychain_count(void) {
    int n = 0;
    for (int i = 0; i < MEM_MAX; i++) {
        n += g_mem[i].present;
    }
    return n;
}

static void test_load_or_create_is_stable(void) {
    unsigned char a[VAULT_MASTER_SECRET_LEN];
    unsigned char b[VAULT_MASTER_SECRET_LEN];
    TEST_ASSERT_EQUAL_INT(0, vault_keychain_load_or_create("vault-A", a));
    TEST_ASSERT_EQUAL_INT(0, vault_keychain_load_or_create("vault-A", b));
    TEST_ASSERT_EQUAL_MEMORY(a, b, VAULT_MASTER_SECRET_LEN); /* same secret on reload */
}

static void test_distinct_vaults_get_distinct_secrets(void) {
    unsigned char a[VAULT_MASTER_SECRET_LEN];
    unsigned char b[VAULT_MASTER_SECRET_LEN];
    TEST_ASSERT_EQUAL_INT(0, vault_keychain_load_or_create("vault-A", a));
    TEST_ASSERT_EQUAL_INT(0, vault_keychain_load_or_create("vault-B", b));
    TEST_ASSERT_NOT_EQUAL(0, memcmp(a, b, VAULT_MASTER_SECRET_LEN));
}

void run_keychain_tests(void) {
    RUN_TEST(test_load_or_create_is_stable);
    RUN_TEST(test_distinct_vaults_get_distinct_secrets);
}
