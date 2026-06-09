/* ECHO stats core — RED stub (ET-5). No-op accumulators + sentinel returns so the Unity
 * contract fails until GREEN; an honest empty stub (MANIFESTO §4). */
#include "stats.h"

void echo_stats_init(echo_stats_t *s) {
    (void)s;
}

void echo_stats_record(echo_stats_t *s, long real, long padding) {
    (void)s;
    (void)real;
    (void)padding;
}

int echo_padding_ratio_pct(const echo_stats_t *s) {
    (void)s;
    return -1;
}

int echo_padding_surge(const echo_stats_t *s, int threshold_pct) {
    (void)s;
    (void)threshold_pct;
    return -1;
}
