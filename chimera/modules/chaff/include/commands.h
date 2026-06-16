/* chaff.* JSON-RPC method dispatch (§5.1 IPC API). Phase B methods work;
 * profile.* return -31004 (deferred to the privileged shim, Sub-D6). */
#ifndef CHAFF_COMMANDS_H
#define CHAFF_COMMANDS_H

#include <pthread.h>
#include <signal.h>
#include <stdint.h>
#include <time.h>

#include <sqlite3.h>

#include "cJSON.h"

#include "endpoints.h"

/* Wire code for profile.* while the privileged shim is unbuilt (§7.10/§8.8). */
#define CHAFF_RPC_PRECONDITION_FAILED (-31004)

typedef enum {
    CHAFF_IDLE = 0,
    CHAFF_GENERATING = 1,
} chaff_state_t;

/* Outbound event awaiting send (mutex-protected singly-linked queue). */
typedef struct chaff_event {
    char *line; /* owned NDJSON frame (no trailing newline) */
    struct chaff_event *next;
} chaff_event_t;

/* Shared daemon runtime. All fields are guarded by `mutex` except `stop`
 * (a signal-safe flag) and `rng_state` (touched only by the generation thread). */
typedef struct {
    chaff_state_t state;
    double multiplier;
    double base_gap_ms; /* default generation gap (no profile in Phase B) */
    double category_weights[5]; /* CHAFF_NUM_CATEGORIES; Phase-A profile weights (flat = no profile) */
    uint64_t requests_today;
    uint64_t bytes_today;
    uint64_t rng_state;
    pthread_mutex_t mutex;
    volatile sig_atomic_t stop;
    chaff_event_t *evq_head;
    chaff_event_t *evq_tail;
    time_t heartbeat_at;
    sqlite3 *db; /* optional generation log; NULL disables logging */
} chaff_runtime_t;

/* Initialise runtime to defaults (IDLE, multiplier = CHAFF_DEFAULT_MULTIPLIER). */
void chaff_runtime_init(chaff_runtime_t *rt);

/* Dispatch a chaff.* method to a malloc'd JSON-RPC response string (caller
 * frees). profile.start/stop return a -31004 error response. */
char *commands_dispatch(chaff_runtime_t *rt, const endpoint_list_t *eps, const char *method,
                        const cJSON *params, const cJSON *id);

#endif /* CHAFF_COMMANDS_H */
