/* ECHO stats core — padding ratio + per-tick padding-ratio decile histogram (§5, ET-1…3).
 * Pure, no I/O (the windowed query + IPC live in later slices). */
#include <stddef.h>

#include "stats.h"

void echo_stats_init(echo_stats_t *s) {
    if (s == NULL) {
        return;
    }
    s->total_real = 0;
    s->total_padding = 0;
    s->ticks = 0;
    for (int i = 0; i < ECHO_HIST_BINS; i++) {
        s->hist[i] = 0;
    }
}

void echo_stats_record(echo_stats_t *s, long real, long padding) {
    if (s == NULL) {
        return;
    }
    if (real < 0) {
        real = 0;
    }
    if (padding < 0) {
        padding = 0;
    }
    s->total_real += real;
    s->total_padding += padding;
    s->ticks += 1;
    long wire = real + padding;
    if (wire <= 0) {
        return; /* a 0-byte wire has no ratio to bin */
    }
    long bin = padding * 100 / wire / 10; /* decile 0..10 */
    if (bin >= ECHO_HIST_BINS) {
        bin = ECHO_HIST_BINS - 1; /* clamp 100% into the top bin */
    }
    s->hist[bin] += 1;
}

int echo_padding_ratio_pct(const echo_stats_t *s) {
    if (s == NULL) {
        return 0;
    }
    long wire = s->total_real + s->total_padding;
    if (wire <= 0) {
        return 0;
    }
    return (int)(s->total_padding * 100 / wire);
}

int echo_padding_surge(const echo_stats_t *s, int threshold_pct) {
    return echo_padding_ratio_pct(s) >= threshold_pct;
}
