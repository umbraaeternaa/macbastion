/* PURGE IPC command dispatch — purge.* methods over JSON-RPC (§7 IPC API, PD-2).
 * The hermetic heart of the daemon: method + params -> a response built from the plan +
 * targets + config cores. purge.trigger is GATED — the real destruction engine is not
 * built, so it returns -31004 (no faked destruction; MANIFESTO §4 / §6). */
#ifndef PURGE_COMMANDS_H
#define PURGE_COMMANDS_H

#include "cJSON.h"

#include "config.h"
#include "targets.h"

typedef struct {
    purge_targets_t targets;
    purge_config_t config;
    int armed;
} purge_runtime_t;

/* Initialise runtime: empty target registry, default config, disarmed. */
void purge_runtime_init(purge_runtime_t *rt);

/* Dispatch a purge.* method to a malloc'd JSON-RPC response string (caller frees).
 * params/id are borrowed. NULL on a NULL method/runtime. */
char *purge_commands_dispatch(purge_runtime_t *rt, const char *method,
                              const cJSON *params, const cJSON *id);

#endif /* PURGE_COMMANDS_H */
