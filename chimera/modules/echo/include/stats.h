/* ECHO stats core — padding ratio + per-tick padding-ratio histogram (§5, ET-1…3). Pure. */
#ifndef ECHO_STATS_H
#define ECHO_STATS_H

#define ECHO_HIST_BINS 10 /* deciles of per-tick padding ratio: bin i = [i*10, i*10+10)% */

typedef struct {
    long total_real;
    long total_padding;
    long ticks;
    long hist[ECHO_HIST_BINS];
} echo_stats_t;

/* Zero all counters. */
void echo_stats_init(echo_stats_t *s);

/* Accumulate one tick's (real, padding) bytes and bump the decile bin for THIS tick's
 * padding ratio (a wire of 0 bytes is ignored). Negative inputs clamp to 0. */
void echo_stats_record(echo_stats_t *s, long real, long padding);

/* Overall padding share as a percent 0..100 (padding / (real + padding)); 0 if empty. */
int echo_padding_ratio_pct(const echo_stats_t *s);

/* 1 if the overall padding ratio >= threshold_pct (the §5 echo.padding.surge trigger). */
int echo_padding_surge(const echo_stats_t *s, int threshold_pct);

#endif /* ECHO_STATS_H */
