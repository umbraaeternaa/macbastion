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

/* Pinned mouse-ratio numbers (spec disambiguation, like temporal.py's constants). */
#define MIRROR_MOUSE_STRAIGHT_FLOOR 1.0 /* px floor on net displacement (avoid blow-up) */
#define MIRROR_MOUSE_RATIO_MAX 10.0     /* cap a wandering path (back-and-forth -> max) */

typedef struct {
    uint64_t chars;    /* printable key-downs in the current window */
    uint64_t deletes;  /* backspace/delete key-downs in the current window */
    double mouse_path; /* summed |move| segment lengths this window */
    double net_dx;     /* net mouse displacement x over the window */
    double net_dy;     /* net mouse displacement y over the window */
} mirror_inputagg_t;

/* Zero the window. */
void inputagg_reset(mirror_inputagg_t *a);

/* Record one keystroke: is_delete != 0 -> a delete/backspace, else a printable char. */
void inputagg_key(mirror_inputagg_t *a, int is_delete);

/* Record one mouse-move delta (px). Accumulates path length + net displacement. */
void inputagg_mouse_move(mirror_inputagg_t *a, double dx, double dy);

/* Mouse path-inefficiency ratio: total path / straight-line (net) displacement, the net
 * floored at MIRROR_MOUSE_STRAIGHT_FLOOR and the ratio capped at MIRROR_MOUSE_RATIO_MAX.
 * 0.0 when there was no movement this window (-> group-A mouse signal absent). */
double inputagg_mouse_ratio(const mirror_inputagg_t *a);

/* Snapshot the window into *out, then reset *a for the next minute (atomic per-minute
 * roll). Both pointers must be non-NULL. */
void inputagg_roll(mirror_inputagg_t *a, mirror_inputagg_t *out);

#endif /* MIRROR_INPUTAGG_H */
