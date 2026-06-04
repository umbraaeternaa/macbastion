/* exclude — per-app passthrough list (§5.4 §3 step 2, §5 mirror.exclude.*).
 * Bundle ids of apps MIRROR must leave untouched (games, drawing tablets, etc.).
 * Fixed-capacity, in-memory; persistence is the daemon's config concern. */
#ifndef MIRROR_EXCLUDE_H
#define MIRROR_EXCLUDE_H

#include <stdbool.h>
#include <stddef.h>

#include "mirror.h"

#define MIRROR_MAX_EXCLUSIONS 64
#define MIRROR_BUNDLE_ID_MAX 256

typedef struct {
    char items[MIRROR_MAX_EXCLUSIONS][MIRROR_BUNDLE_ID_MAX];
    size_t count;
} exclusion_list_t;

/* True if `bundle_id` is on the list (exact match). NULL inputs -> false. */
bool exclude_match(const exclusion_list_t *list, const char *bundle_id);

/* Add a bundle id. Idempotent (re-adding an existing id is a no-op, still OK).
 * MIRROR_ERR if the list is full or the id is too long; MIRROR_OK otherwise. */
mirror_result_t exclude_add(exclusion_list_t *list, const char *bundle_id);

/* Remove a bundle id. MIRROR_ERR_NOTFOUND if absent; MIRROR_OK on removal. */
mirror_result_t exclude_remove(exclusion_list_t *list, const char *bundle_id);

#endif /* MIRROR_EXCLUDE_H */
