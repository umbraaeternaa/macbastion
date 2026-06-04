/* commands — STUB (RED-B). Real chaff.* dispatch lands in GREEN. */
#include "commands.h"

void chaff_runtime_init(chaff_runtime_t *rt) {
    (void)rt; /* TODO(green): set IDLE + default multiplier + zero counters */
}

char *commands_dispatch(chaff_runtime_t *rt, const endpoint_list_t *eps, const char *method,
                        const cJSON *params, const cJSON *id) {
    (void)rt;
    (void)eps;
    (void)method;
    (void)params;
    (void)id;
    return NULL; /* TODO(green): route chaff.* methods; profile.* -> -31004 */
}
