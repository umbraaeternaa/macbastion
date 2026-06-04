/* endpoints — endpoints.json parse + per-category uniform pick (§5.1). */
#include "endpoints.h"

#include <stdlib.h>
#include <string.h>

#include "cJSON.h"

static char *dupstr(const char *s) {
    if (!s) {
        return NULL;
    }
    size_t n = strlen(s) + 1;
    char *p = malloc(n);
    if (p) {
        memcpy(p, s, n);
    }
    return p;
}

chaff_result_t endpoints_parse(const char *json, endpoint_list_t **out) {
    if (!json || !out) {
        return CHAFF_ERR;
    }
    *out = NULL;
    cJSON *root = cJSON_Parse(json);
    if (!root) {
        return CHAFF_ERR_PARSE;
    }
    cJSON *arr = cJSON_GetObjectItemCaseSensitive(root, "endpoints");
    if (!cJSON_IsArray(arr)) {
        cJSON_Delete(root);
        return CHAFF_ERR_PARSE;
    }
    size_t n = (size_t)cJSON_GetArraySize(arr);
    endpoint_list_t *list = malloc(sizeof(*list));
    if (!list) {
        cJSON_Delete(root);
        return CHAFF_ERR;
    }
    list->count = 0;
    list->items = n ? calloc(n, sizeof(endpoint_t)) : NULL;
    if (n && !list->items) {
        free(list);
        cJSON_Delete(root);
        return CHAFF_ERR;
    }
    cJSON *item = NULL;
    cJSON_ArrayForEach(item, arr) {
        cJSON *url = cJSON_GetObjectItemCaseSensitive(item, "url");
        cJSON *cat = cJSON_GetObjectItemCaseSensitive(item, "category");
        if (!cJSON_IsString(url) || !cJSON_IsString(cat)) {
            endpoints_free(list);
            cJSON_Delete(root);
            return CHAFF_ERR_PARSE;
        }
        char *u = dupstr(url->valuestring);
        char *c = dupstr(cat->valuestring);
        if (!u || !c) {
            free(u);
            free(c);
            endpoints_free(list);
            cJSON_Delete(root);
            return CHAFF_ERR;
        }
        list->items[list->count].url = u;
        list->items[list->count].category = c;
        list->count++;
    }
    cJSON_Delete(root);
    *out = list;
    return CHAFF_OK;
}

void endpoints_free(endpoint_list_t *list) {
    if (!list) {
        return;
    }
    for (size_t i = 0; i < list->count; i++) {
        free(list->items[i].url);
        free(list->items[i].category);
    }
    free(list->items);
    free(list);
}

size_t endpoints_count_category(const endpoint_list_t *list, const char *category) {
    if (!list || !category) {
        return 0;
    }
    size_t c = 0;
    for (size_t i = 0; i < list->count; i++) {
        if (strcmp(list->items[i].category, category) == 0) {
            c++;
        }
    }
    return c;
}

const endpoint_t *endpoints_pick(const endpoint_list_t *list, const char *category,
                                 uint64_t *rng_state) {
    if (!list || !category || !rng_state) {
        return NULL;
    }
    size_t total = endpoints_count_category(list, category);
    if (total == 0) {
        return NULL;
    }
    size_t target = (size_t)(chaff_rng_next(rng_state) % total);
    size_t seen = 0;
    for (size_t i = 0; i < list->count; i++) {
        if (strcmp(list->items[i].category, category) == 0) {
            if (seen == target) {
                return &list->items[i];
            }
            seen++;
        }
    }
    return NULL; /* unreachable: target < total */
}
