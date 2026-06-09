/* ECHO IPC command dispatch — RED stub (ED-5). No init, no response, so the Unity
 * contract fails until GREEN; an honest empty stub (MANIFESTO §4). */
#include "commands.h"

void echo_runtime_init(echo_runtime_t *rt) {
    (void)rt;
}

char *echo_commands_dispatch(echo_runtime_t *rt, const char *method, const cJSON *params,
                             const cJSON *id) {
    (void)rt;
    (void)method;
    (void)params;
    (void)id;
    return NULL;
}
