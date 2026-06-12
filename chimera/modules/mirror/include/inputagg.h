/* inputagg — per-minute USER-input aggregator for PULSE group-A (§5.4 + PULSE spec §3).
 *
 * MIRROR observes the operator's input through a passive tap (manual-tier) and keeps
 * ONLY per-window aggregate counters here — privacy §8: never a key code, never a
 * coordinate, never payload. PULSE consumes these as group-A fatigue signals (chars ->
 * typing_speed, deletes/chars -> error_rate). This is SEPARATE from stats.c, which
 * counts MIRROR's OWN injected events. Slice 1: keystroke counts; the mouse path-length
 * ratio is a later slice. */
#ifndef MIRROR_INPUTAGG_H
#define MIRROR_INPUTAGG_H

#include <stdint.h>

typedef struct {
    uint64_t chars;   /* printable key-downs in the current window */
    uint64_t deletes; /* backspace/delete key-downs in the current window */
} mirror_inputagg_t;

/* Zero the window. */
void inputagg_reset(mirror_inputagg_t *a);

/* Record one keystroke: is_delete != 0 -> a delete/backspace, else a printable char. */
void inputagg_key(mirror_inputagg_t *a, int is_delete);

/* Snapshot the window into *out, then reset *a for the next minute (atomic per-minute
 * roll). Both pointers must be non-NULL. */
void inputagg_roll(mirror_inputagg_t *a, mirror_inputagg_t *out);

#endif /* MIRROR_INPUTAGG_H */
