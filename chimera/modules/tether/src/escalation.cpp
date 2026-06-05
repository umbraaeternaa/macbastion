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
    (void)t0_ms; /* RED: GREEN sets base_ms_ (+ suspicious_delay on INSTANT_DROP). */
    (void)how;
    (void)cfg_;
}

EscalationDecision EscalationLadder::evaluate(long now_ms) {
    (void)now_ms; /* RED: GREEN computes the highest due stage from base_ms_+cfg_. */
    (void)cfg_;
    (void)base_ms_;
    return EscalationDecision{Stage::NONE, false, 0};
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
