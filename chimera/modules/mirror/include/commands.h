/* mirror.* JSON-RPC method dispatch (§5.4 §5 IPC API). status, profile.set,
 * exclude add/remove/list and stats work on the in-memory runtime; mirror.enable
 * returns -31004 (Sub-M1) since the CGEventTap install is GATED on signing + TCC. */
#ifndef MIRROR_COMMANDS_H
#define MIRROR_COMMANDS_H

#include <pthread.h>
#include <signal.h>
#include <stdint.h>
#include <time.h>

#include "cJSON.h"

#include "exclude.h"
#include "profile.h"
#include "stats.h"

/* Wire code for mirror.enable while code-signing + Accessibility TCC are unbuilt
 * (§6/§9). PRECONDITION_FAILED, same value CHAFF uses for its gated methods. */
#define MIRROR_RPC_PRECONDITION_FAILED (-31004)

/* Outbound event awaiting send (mutex-protected singly-linked queue). */
typedef struct mirror_event_node {
    char *line; /* owned NDJSON frame (no trailing newline) */
    struct mirror_event_node *next;
} mirror_event_node_t;

/* Shared daemon runtime. Fields are guarded by `mutex` except `stop`
 * (signal-safe) and `rng_state` (touched only by the tap thread, once it exists). */
typedef struct {
    int enabled;             /* tap active? stays 0 until signing + TCC */
    mirror_profile_t profile; /* active profile */
    exclusion_list_t exclusions;
    mirror_stats_t stats;
    uint64_t rng_state;
    pthread_mutex_t mutex;
    volatile sig_atomic_t stop;
    mirror_event_node_t *evq_head;
    mirror_event_node_t *evq_tail;
    time_t heartbeat_at;
} mirror_runtime_t;

/* Initialise runtime to defaults (disabled, profile = MIRROR_PROFILE_DEFAULT,
 * empty exclusions, zero stats). */
void mirror_runtime_init(mirror_runtime_t *rt);

/* Dispatch a mirror.* method to a malloc'd JSON-RPC response string (caller
 * frees). mirror.enable returns a -31004 error response. NULL on allocation
 * failure. */
char *commands_dispatch(mirror_runtime_t *rt, const char *method, const cJSON *params,
                        const cJSON *id);

/* Accessibility-permission probe seam (AX-1, MIRROR signing arc). The real default
 * queries AXIsProcessTrusted(); tests inject a deterministic stub. Pass NULL to reset
 * to the real probe. mirror.enable consults this to give an HONEST, specific reason
 * (Accessibility not granted vs. code-signing not yet built) instead of one blanket
 * "not built" error. The function returns nonzero when the process IS trusted. */
void mirror_set_accessibility_check(int (*fn)(void));

#endif /* MIRROR_COMMANDS_H */
