/* VAULT IPC command dispatch — vault.* methods over JSON-RPC (§7 IPC API). The full engine is
 * real and wired (VD-1..VD-9b): vault.status / create / list / unlock / lock / policy.update /
 * add_file / delete all run real handlers — Keychain KEK, Argon2id KDF, XChaCha20-Poly1305
 * seal/open, RAM-backed mount. No stubs, no faked behaviour (MANIFESTO §4). */
#ifndef VAULT_COMMANDS_H
#define VAULT_COMMANDS_H

#include <time.h> /* time_t for vault_uptime_seconds */

#include "cJSON.h"

#include "vault.h" /* VaultContext / VaultDecision */

typedef struct {
    char open_vault_id[64]; /* empty = no vault unlocked; set on ALLOW (VD-4a) */
    char meta_dir[1024];    /* <state_dir>/vault — where the vault registry persists (VD-2) */
    long relock_at;         /* epoch seconds of the auto-relock deadline; 0 = no timer (VD-4c) */
} vault_runtime_t;

void vault_runtime_init(vault_runtime_t *rt);

/* Auto-relock tick (VD-4c): if a relock timer is armed and `now` has reached it, lock the open
 * vault (clear the open state + timer). The daemon loop calls this each iteration. */
void vault_runtime_tick(vault_runtime_t *rt, long now);

/* Dispatch one vault.* request to a malloc'd JSON-RPC response string (caller frees), or NULL. */
char *vault_commands_dispatch(vault_runtime_t *rt, const char *method, const cJSON *params,
                              const cJSON *id);

/* The unlock context provider (VD-4a): fills a VaultContext for vault.unlock. Default reads the
 * clock (module signals unknown); tests inject a fixed context. NULL resets to the default.
 * Returns the previous provider. */
typedef void (*vault_context_fn)(VaultContext *out);
vault_context_fn vault_set_context_provider(vault_context_fn fn);

/* Pure helper (VD-4a): seconds elapsed since boot from `now` and the kernel boot time (both
 * epoch seconds), clamped to >= 0. Exposed for hermetic testing; default_context feeds it the
 * real sysctl kern.boottime. */
long vault_uptime_seconds(time_t now, time_t boottime_sec);

#endif /* VAULT_COMMANDS_H */
