/* PURGE Tier-2 target registry — bounded in-memory store + dry-run bridge (§3/§7, PR-1…4).
 * Pure (no malloc, no I/O); persistence + IPC live in later slices. */
#include <stddef.h>
#include <string.h>

#include "targets.h"

void purge_targets_init(purge_targets_t *r) {
    if (r != NULL) {
        r->count = 0;
    }
}

static int find_index(const purge_targets_t *r, const char *path) {
    for (int i = 0; i < r->count; i++) {
        if (strcmp(r->items[i].path, path) == 0) {
            return i;
        }
    }
    return -1;
}

int purge_target_add(purge_targets_t *r, const char *path, int encrypted) {
    if (r == NULL || path == NULL || path[0] == '\0' || strlen(path) >= PURGE_PATH_MAX) {
        return -1;
    }
    int idx = find_index(r, path);
    if (idx >= 0) {
        r->items[idx].encrypted = encrypted ? 1 : 0; /* idempotent: update, no dup */
        return r->count;
    }
    if (r->count >= PURGE_MAX_TARGETS) {
        return -1; /* full */
    }
    purge_target_t *t = &r->items[r->count];
    strncpy(t->path, path, PURGE_PATH_MAX - 1);
    t->path[PURGE_PATH_MAX - 1] = '\0';
    t->encrypted = encrypted ? 1 : 0;
    r->count += 1;
    return r->count;
}

int purge_target_remove(purge_targets_t *r, const char *path) {
    if (r == NULL) {
        return -1;
    }
    if (path != NULL) {
        int idx = find_index(r, path);
        if (idx >= 0) {
            for (int i = idx; i < r->count - 1; i++) {
                r->items[i] = r->items[i + 1];
            }
            r->count -= 1;
        }
    }
    return r->count;
}

int purge_target_count(const purge_targets_t *r) {
    return r != NULL ? r->count : 0;
}

const purge_target_t *purge_target_at(const purge_targets_t *r, int i) {
    if (r == NULL || i < 0 || i >= r->count) {
        return NULL;
    }
    return &r->items[i];
}

purge_plan_t purge_plan_targets(const purge_targets_t *r, int tier1_enabled,
                                int tier2_enabled) {
    int enc[PURGE_MAX_TARGETS];
    int n = 0;
    if (r != NULL) {
        n = r->count;
        for (int i = 0; i < n; i++) {
            enc[i] = r->items[i].encrypted;
        }
    }
    return purge_build_plan(enc, n, tier1_enabled, tier2_enabled);
}
