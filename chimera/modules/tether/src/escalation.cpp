/* escalation — time-gated ladder grace→L1→L2→L3 (§3). EMIT-ONLY: computes which
 * stage to request; never acts (core enforces, spec §5).
 *
 * RED STUB (Slice 1): on_absent() does not schedule and evaluate() always returns
 * NONE. GREEN schedules from t0 (+suspicious_delay on INSTANT_DROP), gates L3 on
 * l3_armed, and cancels on recovery. */
#include "escalation.hpp"

namespace tether {

EscalationLadder::EscalationLadder(EscalationConfig cfg)
    : cfg_(cfg), active_(false), base_ms_(0), last_stage_(Stage::NONE) {}

void EscalationLadder::on_absent(long t0_ms, Disappearance how) {
    /* INSTANT_DROP is suspicious (possible jamming): shift the whole schedule
     * later so a jammer SLOWS the ladder, never speeds it (§8 anti-weaponization). */
    base_ms_ = t0_ms + (how == Disappearance::INSTANT_DROP ? cfg_.suspicious_delay_ms : 0);
    active_ = true;
    last_stage_ = Stage::NONE;
}

EscalationDecision EscalationLadder::evaluate(long now_ms) {
    if (!active_) {
        return EscalationDecision{Stage::NONE, false, 0};
    }
    const long l1_at = base_ms_ + cfg_.grace_ms;
    const long l2_at = l1_at + cfg_.l1_to_l2_ms;
    const long l3_at = l2_at + cfg_.l2_to_l3_ms;

    Stage stage;
    long next_at; /* when the next stage fires (== now once terminal) */
    if (now_ms < l1_at) {
        stage = Stage::NONE;
        next_at = l1_at;
    } else if (now_ms < l2_at) {
        stage = Stage::L1;
        next_at = l2_at;
    } else if (!cfg_.l3_armed || now_ms < l3_at) {
        /* L3 is opt-in: disarmed, the ladder caps at L2 and never reaches PURGE. */
        stage = Stage::L2;
        next_at = cfg_.l3_armed ? l3_at : now_ms;
    } else {
        stage = Stage::L3;
        next_at = now_ms; /* terminal */
    }

    long grace_remaining = next_at - now_ms;
    if (grace_remaining < 0) {
        grace_remaining = 0;
    }
    const bool changed = (stage != last_stage_);
    last_stage_ = stage;
    return EscalationDecision{stage, changed, grace_remaining};
}

void EscalationLadder::on_recovered() {
    active_ = false;
    last_stage_ = Stage::NONE;
}

void EscalationLadder::cancel() {
    active_ = false;
    last_stage_ = Stage::NONE;
}

Stage EscalationLadder::current_stage() const { return last_stage_; }
bool EscalationLadder::active() const { return active_; }

} // namespace tether
