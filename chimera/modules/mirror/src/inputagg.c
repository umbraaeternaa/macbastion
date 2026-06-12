/* Per-minute USER-input aggregator (PULSE group-A producer, slice 1). Counts only —
 * privacy §8: no key code, no coordinate, no payload ever touches this. */
#include "inputagg.h"

void inputagg_reset(mirror_inputagg_t *a) {
    a->chars = 0;
    a->deletes = 0;
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
