/* ECHO shaper core — constant-rate padding decision (§5.2 §3, ES-2). Pure, no I/O. */
#ifndef ECHO_SHAPER_H
#define ECHO_SHAPER_H

/* One tick's decision: how many real bytes to send + how many padding bytes to emit.
 * The on-wire total is real_send + padding. */
typedef struct {
    long real_send;
    long padding;
} echo_decision_t;

/* Steady bytes allowed per tick for target_kbps at tick_ms
 * (e.g. 100 KB/s @ 10ms -> 100*1024*10/1000 = 1024). Returns 0 for non-positive inputs. */
long echo_budget_bytes(int target_kbps, int tick_ms);

/* Constant-rate decision for one tick (ES-2/ES-3):
 *   real_send = min(queued, budget + burst)
 *   padding   = max(0, budget - real_send)
 * so the wire stays FLAT at `budget` whenever queued <= budget (the hiding guarantee),
 * and bursts up to budget+burst to drain a backlog. Negative inputs clamp to 0;
 * budget <= 0 yields {0, 0}. */
echo_decision_t echo_shape(long queued, long budget, long burst);

#endif /* ECHO_SHAPER_H */
