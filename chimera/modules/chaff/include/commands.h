/* chaff.* JSON-RPC method dispatch (§5.1 IPC API). Phase B methods work;
 * profile.* return -31004 (deferred to the privileged shim, Sub-D6). */
#ifndef CHAFF_COMMANDS_H
#define CHAFF_COMMANDS_H

#include <stdint.h>

#include "cJSON.h"

#include "endpoints.h"

/* Wire code for profile.* while the privileged shim is unbuilt (§7.10/§8.8). */
#define CHAFF_RPC_PRECONDITION_FAILED (-31004)

typedef enum {
    CHAFF_IDLE = 0,
    CHAFF_GENERATING = 1,
} chaff_state_t;

typedef struct {
    chaff_state_t state;
    double multiplier;
    uint64_t requests_today;
    uint64_t bytes_today;
} chaff_runtime_t;

/* Initialise runtime to defaults (IDLE, multiplier = CHAFF_DEFAULT_MULTIPLIER). */
void chaff_runtime_init(chaff_runtime_t *rt);

/* Dispatch a chaff.* method to a malloc'd JSON-RPC response string (caller
 * frees). profile.start/stop return a -31004 error response. */
char *commands_dispatch(chaff_runtime_t *rt, const endpoint_list_t *eps, const char *method,
                        const cJSON *params, const cJSON *id);

#endif /* CHAFF_COMMANDS_H */
