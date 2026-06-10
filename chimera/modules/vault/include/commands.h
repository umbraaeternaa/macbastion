/* VAULT IPC command dispatch — vault.* methods over JSON-RPC (§7 IPC API, VD-1).
 * VD-1 skeleton: vault.status is real; the engine methods (create / list / unlock / lock /
 * policy.update / add_file / delete) are gated -31004 — not built, no faked behaviour
 * (MANIFESTO §4). The keychain KEK + unlock engine land in later slices. */
#ifndef VAULT_COMMANDS_H
#define VAULT_COMMANDS_H

#include "cJSON.h"

typedef struct {
    char open_vault_id[64]; /* empty = no vault unlocked (VD-1: always empty) */
} vault_runtime_t;

void vault_runtime_init(vault_runtime_t *rt);

/* Dispatch one vault.* request to a malloc'd JSON-RPC response string (caller frees), or NULL. */
char *vault_commands_dispatch(vault_runtime_t *rt, const char *method, const cJSON *params,
                              const cJSON *id);

#endif /* VAULT_COMMANDS_H */
