/* stats — RED-B stub. Increment is a no-op, get always 0, so the counter tests
 * fail honestly. Real cumulative counters land in GREEN. */
#include "stats.h"

void stats_increment(mirror_stats_t *s, mirror_event_t type) {
    (void)s;
    (void)type;
    /* stub: counts nothing */
}

uint64_t stats_get(const mirror_stats_t *s, mirror_event_t type) {
    (void)s;
    (void)type;
    return 0; /* stub */
}
