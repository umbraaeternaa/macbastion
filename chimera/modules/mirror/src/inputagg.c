/* Per-minute USER-input aggregator (PULSE group-A producer). Counts + geometry only —
 * privacy §8: no key code, no absolute coordinate, no payload ever touches this. */
#include "inputagg.h"

#include <math.h>

void inputagg_reset(mirror_inputagg_t *a) {
    a->chars = 0;
    a->deletes = 0;
    a->mouse_path = 0.0;
    a->net_dx = 0.0;
    a->net_dy = 0.0;
}

void inputagg_key(mirror_inputagg_t *a, int is_delete) {
    if (is_delete) {
        a->deletes++;
    } else {
        a->chars++;
    }
}

void inputagg_roll(mirror_inputagg_t *a, mirror_inputagg_t *out) {
    *out = *a;
    inputagg_reset(a);
}

void inputagg_mouse_move(mirror_inputagg_t *a, double dx, double dy) {
    a->mouse_path += hypot(dx, dy);
    a->net_dx += dx;
    a->net_dy += dy;
}

double inputagg_mouse_ratio(const mirror_inputagg_t *a) {
    if (a->mouse_path <= 0.0) {
        return 0.0; /* no movement this window -> group-A mouse signal absent */
    }
    double straight = hypot(a->net_dx, a->net_dy);
    if (straight < MIRROR_MOUSE_STRAIGHT_FLOOR) {
        straight = MIRROR_MOUSE_STRAIGHT_FLOOR; /* floor: tiny net would blow the ratio up */
    }
    double ratio = a->mouse_path / straight;
    if (ratio > MIRROR_MOUSE_RATIO_MAX) {
        ratio = MIRROR_MOUSE_RATIO_MAX; /* cap a wandering/back-and-forth path */
    }
    return ratio;
}
