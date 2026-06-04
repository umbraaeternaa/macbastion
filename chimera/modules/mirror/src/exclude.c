/* exclude — per-app passthrough list (§5.4 §3, §5 mirror.exclude.*). Fixed-capacity
 * fixed-width buffer (no malloc — the whole list lives inside the runtime struct). */
#include "exclude.h"

#include <stdio.h>
#include <string.h>

/* Index of bundle_id in the list, or -1 if absent. */
static long find(const exclusion_list_t *list, const char *bundle_id) {
    for (size_t i = 0; i < list->count; i++) {
        if (strcmp(list->items[i], bundle_id) == 0) {
            return (long)i;
        }
    }
    return -1;
}

bool exclude_match(const exclusion_list_t *list, const char *bundle_id) {
    if (!list || !bundle_id) {
        return false;
    }
    return find(list, bundle_id) >= 0;
}

mirror_result_t exclude_add(exclusion_list_t *list, const char *bundle_id) {
    if (!list || !bundle_id) {
        return MIRROR_ERR;
    }
    if (strlen(bundle_id) >= MIRROR_BUNDLE_ID_MAX) {
        return MIRROR_ERR;
    }
    if (find(list, bundle_id) >= 0) {
        return MIRROR_OK; /* idempotent: already present */
    }
    if (list->count >= MIRROR_MAX_EXCLUSIONS) {
        return MIRROR_ERR; /* full */
    }
    /* fits: bounded by the strlen check above */
    snprintf(list->items[list->count], MIRROR_BUNDLE_ID_MAX, "%s", bundle_id);
    list->count++;
    return MIRROR_OK;
}

mirror_result_t exclude_remove(exclusion_list_t *list, const char *bundle_id) {
    if (!list || !bundle_id) {
        return MIRROR_ERR;
    }
    long idx = find(list, bundle_id);
    if (idx < 0) {
        return MIRROR_ERR_NOTFOUND;
    }
    /* shift the tail down one slot to keep [0, count) contiguous */
    for (size_t i = (size_t)idx; i + 1 < list->count; i++) {
        memcpy(list->items[i], list->items[i + 1], MIRROR_BUNDLE_ID_MAX);
    }
    list->count--;
    return MIRROR_OK;
}
