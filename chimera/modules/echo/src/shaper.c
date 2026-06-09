/* ECHO shaper core — constant-rate padding decision (§5.2 §3, ES-2/ES-3). Pure, no I/O.
 *
 * The wire is held FLAT at `budget` whenever the real queue is within budget (idle or
 * light traffic looks identical on the wire); a backlog drains up to budget+burst, where
 * no padding is needed. Inputs are clamped defensively; a non-positive budget is a no-op. */
#include "shaper.h"

long echo_budget_bytes(int target_kbps, int tick_ms) {
    if (target_kbps <= 0 || tick_ms <= 0) {
        return 0;
    }
    return (long)target_kbps * 1024 * tick_ms / 1000;
}

echo_decision_t echo_shape(long queued, long budget, long burst) {
    echo_decision_t d = {0, 0};
    if (budget <= 0) {
        return d; /* no budget configured -> shape nothing */
    }
    if (queued < 0) {
        queued = 0;
    }
    if (burst < 0) {
        burst = 0;
    }
    long allow = budget + burst;
    long real_send = queued < allow ? queued : allow; /* min(queued, budget + burst) */
    long padding = budget - real_send;                /* max(0, budget - real_send) */
    if (padding < 0) {
        padding = 0;
    }
    d.real_send = real_send;
    d.padding = padding;
    return d;
}
