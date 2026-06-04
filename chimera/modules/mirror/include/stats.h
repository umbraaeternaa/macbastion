/* stats — aggregate per-event-type counters (§5.4 §7 privacy invariant). Counts
 * ONLY how many events of each type were shaped — never payload, never coords,
 * never key codes. Cumulative in-memory (Sub-M4); daily rollover is a daemon
 * concern, deferred. */
#ifndef MIRROR_STATS_H
#define MIRROR_STATS_H

#include <stdint.h>

typedef enum {
    MIRROR_EV_MOUSE_MOVE = 0,
    MIRROR_EV_MOUSE_CLICK,
    MIRROR_EV_KEY_DOWN,
    MIRROR_EV_KEY_UP,
    MIRROR_EV_SCROLL,
    MIRROR_EV__COUNT, /* sentinel: number of event types */
} mirror_event_t;

typedef struct {
    uint64_t counts[MIRROR_EV__COUNT];
} mirror_stats_t;

/* Increment the counter for one event type. Out-of-range type is ignored. */
void stats_increment(mirror_stats_t *s, mirror_event_t type);

/* Read the cumulative count for one event type. Out-of-range type -> 0. */
uint64_t stats_get(const mirror_stats_t *s, mirror_event_t type);

#endif /* MIRROR_STATS_H */
