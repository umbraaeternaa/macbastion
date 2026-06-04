/* stats — cumulative per-event-type counters (§5.4 §7). Counts ONLY how many
 * events of each type were shaped — never payload (Sub-M4: in-memory, no reset). */
#include "stats.h"

void stats_increment(mirror_stats_t *s, mirror_event_t type) {
    if (!s || type < 0 || type >= MIRROR_EV__COUNT) {
        return;
    }
    s->counts[type]++;
}

uint64_t stats_get(const mirror_stats_t *s, mirror_event_t type) {
    if (!s || type < 0 || type >= MIRROR_EV__COUNT) {
        return 0;
    }
    return s->counts[type];
}
