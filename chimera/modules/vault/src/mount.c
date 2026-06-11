/* VAULT decrypted-plaintext mount — real backend (VD-9, manual-tier). begin attaches a macOS
 * RAM disk (hdiutil) and formats+mounts it HFS+ under a vault-specific volume name; put writes a
 * decrypted file into it; end detaches it (the RAM and its plaintext vanish). The seam (mount.h)
 * lets tests inject a temp-dir backend, so this real path is exercised live, not in the suite. */
#include "mount.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define VAULT_RAM_SECTORS 65536 /* 65536 * 512 B = 32 MiB RAM disk per vault */
#define MOUNT_MAX 4

static struct {
    char vault_id[64];
    char path[512];
    char device[64];
    int present;
} g_mounts[MOUNT_MAX];

static int slot_for(const char *vault_id) {
    for (int i = 0; i < MOUNT_MAX; i++) {
        if (g_mounts[i].present && strcmp(g_mounts[i].vault_id, vault_id) == 0) {
            return i;
        }
    }
    return -1;
}

static int mount_begin_real(const char *vault_id, char *out, size_t sz) {
    int existing = slot_for(vault_id);
    if (existing >= 0) {
        snprintf(out, sz, "%s", g_mounts[existing].path);
        return 0;
    }
    int slot = -1;
    for (int i = 0; i < MOUNT_MAX; i++) {
        if (!g_mounts[i].present) {
            slot = i;
            break;
        }
    }
    if (slot < 0) {
        return -1;
    }
    /* 1. attach an unformatted RAM disk -> device node (e.g. /dev/disk5) */
    char cmd[256];
    snprintf(cmd, sizeof(cmd), "hdiutil attach -nomount ram://%d 2>/dev/null", VAULT_RAM_SECTORS);
    FILE *p = popen(cmd, "r");
    if (p == NULL) {
        return -1;
    }
    char device[64] = {0};
    char *got = fgets(device, sizeof(device), p);
    pclose(p);
    if (got == NULL) {
        return -1;
    }
    device[strcspn(device, " \t\r\n")] = '\0';
    if (device[0] == '\0') {
        return -1;
    }
    /* 2. format + mount HFS+ under a vault-specific volume name (mounts at /Volumes/<vol>) */
    char vol[80];
    snprintf(vol, sizeof(vol), "CHIMERA-VAULT-%.8s", vault_id);
    snprintf(cmd, sizeof(cmd), "diskutil erasevolume HFS+ '%s' %s >/dev/null 2>&1", vol, device);
    if (system(cmd) != 0) {
        snprintf(cmd, sizeof(cmd), "hdiutil detach %s -force >/dev/null 2>&1", device);
        (void)system(cmd);
        return -1;
    }
    snprintf(g_mounts[slot].vault_id, sizeof(g_mounts[slot].vault_id), "%s", vault_id);
    snprintf(g_mounts[slot].path, sizeof(g_mounts[slot].path), "/Volumes/%s", vol);
    snprintf(g_mounts[slot].device, sizeof(g_mounts[slot].device), "%s", device);
    g_mounts[slot].present = 1;
    snprintf(out, sz, "%s", g_mounts[slot].path);
    return 0;
}

static int mount_put_real(const char *vault_id, const char *name, const unsigned char *data,
                          size_t len) {
    int s = slot_for(vault_id);
    if (s < 0) {
        return -1;
    }
    /* basename only — never let a crafted name escape the mount */
    const char *slash = strrchr(name, '/');
    const char *base = slash ? slash + 1 : name;
    if (base[0] == '\0' || strcmp(base, ".") == 0 || strcmp(base, "..") == 0) {
        return -1;
    }
    char fpath[640];
    snprintf(fpath, sizeof(fpath), "%s/%s", g_mounts[s].path, base);
    FILE *f = fopen(fpath, "wb");
    if (f == NULL) {
        return -1;
    }
    size_t w = (len > 0) ? fwrite(data, 1, len, f) : 0;
    fclose(f);
    return (w == len) ? 0 : -1;
}

static int mount_end_real(const char *vault_id) {
    int s = slot_for(vault_id);
    if (s < 0) {
        return 0; /* nothing mounted is success */
    }
    char cmd[128];
    snprintf(cmd, sizeof(cmd), "hdiutil detach %s -force >/dev/null 2>&1", g_mounts[s].device);
    (void)system(cmd);
    memset(&g_mounts[s], 0, sizeof(g_mounts[s]));
    return 0;
}

static vault_mount_backend_t g_backend = {mount_begin_real, mount_put_real, mount_end_real};

vault_mount_backend_t vault_mount_set_backend(vault_mount_backend_t b) {
    vault_mount_backend_t prev = g_backend;
    g_backend.begin = b.begin ? b.begin : mount_begin_real;
    g_backend.put = b.put ? b.put : mount_put_real;
    g_backend.end = b.end ? b.end : mount_end_real;
    return prev;
}

int vault_mount_begin(const char *vault_id, char *out, size_t sz) {
    if (vault_id == NULL || out == NULL) {
        return -1;
    }
    return g_backend.begin(vault_id, out, sz);
}

int vault_mount_put(const char *vault_id, const char *name, const unsigned char *data, size_t len) {
    if (vault_id == NULL || name == NULL) {
        return -1;
    }
    return g_backend.put(vault_id, name, data, len);
}

int vault_mount_end(const char *vault_id) {
    if (vault_id == NULL) {
        return -1;
    }
    return g_backend.end(vault_id);
}
