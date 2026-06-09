/* ECHO IPC command dispatch — echo.* methods over JSON-RPC (§5 IPC API, ED-2).
 * The hermetic heart of the daemon: method + params -> a response string, built from the
 * config + stats cores. The socket loop (connect/register/serve) is a later slice. */
#ifndef ECHO_COMMANDS_H
#define ECHO_COMMANDS_H

#include "cJSON.h"

#include "config.h"
#include "stats.h"

typedef struct {
    echo_config_t config;
    echo_stats_t stats;
    int running;
} echo_runtime_t;

/* Initialise runtime: default config, zeroed stats, not running. */
void echo_runtime_init(echo_runtime_t *rt);

/* Dispatch an echo.* method to a malloc'd JSON-RPC response string (caller frees).
 * params/id are borrowed (not consumed). NULL on a NULL method/runtime. */
char *echo_commands_dispatch(echo_runtime_t *rt, const char *method,
                             const cJSON *params, const cJSON *id);

#endif /* ECHO_COMMANDS_H */
