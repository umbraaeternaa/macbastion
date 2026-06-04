/* commands — RED-B stub. runtime_init is a no-op (leaves the zeroed struct, so
 * profile reads as LIGHT not the MEDIUM default) and dispatch returns NULL, so
 * the dispatch + enable-deferred tests fail honestly. Real mirror.* handling
 * lands in GREEN. */
#include "commands.h"

#include <stddef.h>

void mirror_runtime_init(mirror_runtime_t *rt) {
    (void)rt;
    /* stub: no initialisation */
}

char *commands_dispatch(mirror_runtime_t *rt, const char *method, const cJSON *params,
                        const cJSON *id) {
    (void)rt;
    (void)method;
    (void)params;
    (void)id;
    return NULL; /* stub */
}
