/* secrets — sensitive-region registry + the real tier3 RAM-wipe action (§5.8 RAM erase).
 * A fixed-capacity table of {ptr,len}; purge_secret_clear_all() calls purge_wipe() on each
 * (optimization-resistant zeroing, dc-zva-accelerated). No allocation on the purge path — the
 * table is static, so a fired purge never has to malloc. Touches only registered process
 * memory; nothing on disk. */
#include "secrets.h"

#include "wipe.h"

typedef struct {
    void  *buf;
    size_t len;
} region_t;

static region_t g_regions[PURGE_SECRET_MAX];
static size_t   g_count = 0;

int purge_secret_register(void *buf, size_t len) {
    if (buf == NULL || len == 0 || g_count >= PURGE_SECRET_MAX) {
        return -1;
    }
    g_regions[g_count].buf = buf;
    g_regions[g_count].len = len;
    g_count++;
    return 0;
}

int purge_secret_clear_all(void) {
    for (size_t i = 0; i < g_count; i++) {
        purge_wipe(g_regions[i].buf, g_regions[i].len);
    }
    return 0;
}

size_t purge_secret_count(void) {
    return g_count;
}

void purge_secret_reset(void) {
    g_count = 0;
}
