/* VAULT per-vault master secret in the macOS login Keychain (§5.6, VD-3). Each vault owns a
 * 32-byte master secret stored as a generic-password item under service "com.umbra.chimera",
 * account = vault_id — the SAME namespace the privileged shim's evict (PURGE Tier-0) deletes.
 * The derived encryption key (Argon2id over master_secret || policy_hash) is computed at unlock
 * and never stored (crypto.c).
 *
 * The SecItem backend is swappable so tests inject an in-memory store and NEVER touch the real
 * login Keychain; the real SecItem path is manual-tier (verified live), like attest/ownership. */
#ifndef VAULT_KEYCHAIN_H
#define VAULT_KEYCHAIN_H

#define VAULT_MASTER_SECRET_LEN 32

/* Backend hooks. load: 1 = found (fills out[32]), 0 = absent, -1 = error. store: 0 ok / -1. */
typedef struct {
    int (*load)(const char *vault_id, unsigned char *out);
    int (*store)(const char *vault_id, const unsigned char *secret);
} vault_keychain_backend_t;

/* Swap the backend (NULL field(s) reset to the real SecItem backend). Returns the previous. */
vault_keychain_backend_t vault_keychain_set_backend(vault_keychain_backend_t b);

/* Get-or-create the vault's master secret. 0 on success (out[VAULT_MASTER_SECRET_LEN] filled),
 * -1 on error. Absent -> generate 32 CSPRNG bytes + store. */
int vault_keychain_load_or_create(const char *vault_id, unsigned char *out);

#endif /* VAULT_KEYCHAIN_H */
