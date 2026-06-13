/* statefiles — CHIMERA-own-file registry + the real tier0 file-removal action (§3, §5.8).
 * A fixed-capacity table of absolute path strings; purge_statefile_remove_all() unlink()s each.
 * register refuses anything that is not an absolute path (must start with '/'), too long, or
 * over capacity — CHIMERA registers only its own files, and the absolute-path rule keeps a
 * stray relative path from resolving against an unexpected cwd. No allocation on the purge
 * path (static table). This deletes files on disk; it is armed-gated upstream. */
#include "statefiles.h"

#include <string.h>
#include <unistd.h>

static char   g_paths[PURGE_STATEFILE_MAX][PURGE_STATEFILE_PATHMAX];
static size_t g_count = 0;

int purge_statefile_register(const char *path) {
    if (path == NULL || path[0] != '/') { /* NULL, empty, or not absolute */
        return -1;
    }
    size_t len = strlen(path);
    if (len >= PURGE_STATEFILE_PATHMAX || g_count >= PURGE_STATEFILE_MAX) {
        return -1;
    }
    memcpy(g_paths[g_count], path, len + 1); /* copy incl NUL */
    g_count++;
    return 0;
}

int purge_statefile_remove_all(void) {
    for (size_t i = 0; i < g_count; i++) {
        unlink(g_paths[i]); /* best-effort: a path already gone is not an error */
    }
    return 0;
}

size_t purge_statefile_count(void) {
    return g_count;
}

void purge_statefile_reset(void) {
    g_count = 0;
}
