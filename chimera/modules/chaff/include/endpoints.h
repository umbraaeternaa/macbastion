/* Endpoint whitelist: parse, query, weighted pick (§5.1). */
#ifndef CHAFF_ENDPOINTS_H
#define CHAFF_ENDPOINTS_H

#include <stddef.h>
#include <stdint.h>

#include "chaff.h"

typedef struct {
    char *url;
    char *category;
} endpoint_t;

typedef struct {
    endpoint_t *items;
    size_t count;
} endpoint_list_t;

/* Parse the endpoints.json document. On CHAFF_OK, *out is an owned list the
 * caller frees with endpoints_free. CHAFF_ERR_PARSE on malformed JSON. */
chaff_result_t endpoints_parse(const char *json, endpoint_list_t **out);
void endpoints_free(endpoint_list_t *list);

/* Number of endpoints in a category. */
size_t endpoints_count_category(const endpoint_list_t *list, const char *category);

/* Pick a random endpoint of the given category (rng_state advanced in place).
 * Returns NULL if the category has no endpoints. */
const endpoint_t *endpoints_pick(const endpoint_list_t *list, const char *category,
                                 uint64_t *rng_state);

#endif /* CHAFF_ENDPOINTS_H */
