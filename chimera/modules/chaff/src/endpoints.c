/* endpoints — STUB (RED-B). Real cJSON parsing + weighted pick land in GREEN. */
#include "endpoints.h"

chaff_result_t endpoints_parse(const char *json, endpoint_list_t **out) {
    (void)json;
    if (out) {
        *out = NULL;
    }
    return CHAFF_ERR; /* TODO(green): parse the endpoints.json document via cJSON */
}

void endpoints_free(endpoint_list_t *list) {
    (void)list; /* TODO(green): free items + list */
}

size_t endpoints_count_category(const endpoint_list_t *list, const char *category) {
    (void)list;
    (void)category;
    return 0; /* TODO(green): count matching endpoints */
}

const endpoint_t *endpoints_pick(const endpoint_list_t *list, const char *category,
                                 uint64_t *rng_state) {
    (void)list;
    (void)category;
    (void)rng_state;
    return NULL; /* TODO(green): weighted pick within category */
}
