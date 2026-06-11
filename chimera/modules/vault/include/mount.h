/* VAULT decrypted-plaintext mount (§5.6, VD-9). On a state-gated unlock the vault's decrypted
 * files are materialised into a RAM-backed mount — they never touch the disk and vanish on lock.
 * The real backend creates a macOS RAM disk via hdiutil (manual-tier, verified live); the seam
 * lets tests inject a temp-dir backend so NO test ever mounts a real volume. */
#ifndef VAULT_MOUNT_H
#define VAULT_MOUNT_H

#include <stddef.h>

/* Backend hooks (all 0 = ok / -1 = error):
 *   begin: create the vault's mount, write its absolute path into out[sz].
 *   put:   place a decrypted file (name -> data[len]) inside the vault's mount.
 *   end:   tear the mount down + wipe its contents. */
typedef struct {
    int (*begin)(const char *vault_id, char *out, size_t sz);
    int (*put)(const char *vault_id, const char *name, const unsigned char *data, size_t len);
    int (*end)(const char *vault_id);
} vault_mount_backend_t;

/* Swap the backend (NULL field(s) reset to the real hdiutil backend). Returns the previous. */
vault_mount_backend_t vault_mount_set_backend(vault_mount_backend_t b);

int vault_mount_begin(const char *vault_id, char *out, size_t sz);
int vault_mount_put(const char *vault_id, const char *name, const unsigned char *data, size_t len);
int vault_mount_end(const char *vault_id);

#endif /* VAULT_MOUNT_H */
