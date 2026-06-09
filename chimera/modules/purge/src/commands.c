/* PURGE IPC command dispatch — RED stub (PD-5). No init, no response, so the Unity
 * contract fails until GREEN; an honest empty stub (MANIFESTO §4). */
#include "commands.h"

void purge_runtime_init(purge_runtime_t *rt) {
    (void)rt;
}

char *purge_commands_dispatch(purge_runtime_t *rt, const char *method, const cJSON *params,
                              const cJSON *id) {
    (void)rt;
    (void)method;
    (void)params;
    (void)id;
    return NULL;
}
