/* VAULT mount seam (VD-9). The real backend is a macOS RAM disk (manual-tier); these hermetic
 * tests inject a temp-dir backend that the runner's setUp installs before EVERY test, so no test
 * ever mounts a real volume. The temp dir stands in for the RAM-backed mount. */
#include "unity.h"

#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "mount.h"
#include "tests.h"

#define TMP_MAX 4
static struct {
    char vault_id[64];
    char path[256];
    int present;
} g_tmp[TMP_MAX];

static int tmp_slot(const char *vault_id) {
    for (int i = 0; i < TMP_MAX; i++) {
        if (g_tmp[i].present && strcmp(g_tmp[i].vault_id, vault_id) == 0) {
            return i;
        }
    }
    return -1;
}

static void rm_rf(const char *dir) {
    DIR *d = opendir(dir);
    if (d != NULL) {
        struct dirent *e;
        while ((e = readdir(d)) != NULL) {
            if (strcmp(e->d_name, ".") == 0 || strcmp(e->d_name, "..") == 0) {
                continue;
            }
            char p[512];
            snprintf(p, sizeof(p), "%s/%s", dir, e->d_name);
            unlink(p);
        }
        closedir(d);
    }
    rmdir(dir);
}

static int tmp_begin(const char *vault_id, char *out, size_t sz) {
    int existing = tmp_slot(vault_id);
    if (existing >= 0) {
        snprintf(out, sz, "%s", g_tmp[existing].path);
        return 0;
    }
    int slot = -1;
    for (int i = 0; i < TMP_MAX; i++) {
        if (!g_tmp[i].present) {
            slot = i;
            break;
        }
    }
    if (slot < 0) {
        return -1;
    }
    char tmpl[256];
    snprintf(tmpl, sizeof(tmpl), "/tmp/chimera-vault-mount-XXXXXX");
    char *dir = mkdtemp(tmpl);
    if (dir == NULL) {
        return -1;
    }
    snprintf(g_tmp[slot].vault_id, sizeof(g_tmp[slot].vault_id), "%s", vault_id);
    snprintf(g_tmp[slot].path, sizeof(g_tmp[slot].path), "%s", dir);
    g_tmp[slot].present = 1;
    snprintf(out, sz, "%s", dir);
    return 0;
}

static int tmp_put(const char *vault_id, const char *name, const unsigned char *data, size_t len) {
    int s = tmp_slot(vault_id);
    if (s < 0) {
        return -1;
    }
    const char *slash = strrchr(name, '/');
    const char *base = slash ? slash + 1 : name;
    char fpath[512];
    snprintf(fpath, sizeof(fpath), "%s/%s", g_tmp[s].path, base);
    FILE *f = fopen(fpath, "wb");
    if (f == NULL) {
        return -1;
    }
    size_t w = (len > 0) ? fwrite(data, 1, len, f) : 0;
    fclose(f);
    return (w == len) ? 0 : -1;
}

static int tmp_end(const char *vault_id) {
    int s = tmp_slot(vault_id);
    if (s < 0) {
        return 0;
    }
    rm_rf(g_tmp[s].path);
    memset(&g_tmp[s], 0, sizeof(g_tmp[s]));
    return 0;
}

/* Installed by the runner's setUp: tear down any leftover temp mounts + swap in the temp backend. */
void vault_test_install_tmp_mount(void) {
    for (int i = 0; i < TMP_MAX; i++) {
        if (g_tmp[i].present) {
            rm_rf(g_tmp[i].path);
        }
    }
    memset(g_tmp, 0, sizeof(g_tmp));
    vault_mount_backend_t b = {tmp_begin, tmp_put, tmp_end};
    vault_mount_set_backend(b);
}

static void test_mount_begin_put_end_roundtrip(void) {
    char path[256];
    TEST_ASSERT_EQUAL_INT(0, vault_mount_begin("vault-M", path, sizeof(path)));
    TEST_ASSERT_TRUE(path[0] != '\0');
    TEST_ASSERT_EQUAL_INT(0, vault_mount_put("vault-M", "note.txt", (const unsigned char *)"hi", 2));

    char fp[320];
    snprintf(fp, sizeof(fp), "%s/note.txt", path);
    FILE *f = fopen(fp, "rb");
    TEST_ASSERT_NOT_NULL(f);
    char buf[8] = {0};
    size_t n = fread(buf, 1, sizeof(buf) - 1, f);
    fclose(f);
    buf[n] = '\0';
    TEST_ASSERT_EQUAL_STRING("hi", buf);

    TEST_ASSERT_EQUAL_INT(0, vault_mount_end("vault-M"));
    TEST_ASSERT_NULL(fopen(fp, "rb")); /* torn down — the plaintext is gone */
}

static void test_mount_put_without_begin_fails(void) {
    TEST_ASSERT_EQUAL_INT(-1, vault_mount_put("never-mounted", "x", (const unsigned char *)"y", 1));
}

void run_mount_tests(void) {
    RUN_TEST(test_mount_begin_put_end_roundtrip);
    RUN_TEST(test_mount_put_without_begin_fails);
}
