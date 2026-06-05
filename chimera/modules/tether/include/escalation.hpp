/* Escalation ladder (§3, time-gated). On confirmed ABSENT the ladder schedules
 * L1 (lock screen), L2 (lock vaults), L3 (PURGE — opt-in) at grace / +l1_to_l2 /
 * +l2_to_l3 after the absence. evaluate(now) reports the highest stage now due.
 *
 * EMIT-ONLY (spec §5): this computes WHICH stage to request; it never performs
 * lock/evict/reboot. Core enforces the action from the emitted tether.escalation.
 *
 * Anti-weaponization: an INSTANT_DROP shifts the whole schedule later by
 * suspicious_delay_ms — jamming slows the ladder, never speeds it. L3 is reached
 * only when l3_armed. on_recovered()/cancel() clear a pending (reversible) ladder. */
#ifndef TETHER_ESCALATION_HPP
#define TETHER_ESCALATION_HPP

#include "tether.hpp"

namespace tether {

struct EscalationDecision {
    Stage stage;            /* highest stage due at the queried time (NONE if none) */
    bool changed;           /* did the due stage advance since the last evaluate? */
    long grace_remaining_ms; /* until the NEXT stage fires (0 once at L3 / none) */
};

class EscalationLadder {
  public:
    explicit EscalationLadder(EscalationConfig cfg);

    /* Begin the ladder at absence time t0_ms; `how` may delay the schedule. */
    void on_absent(long t0_ms, Disappearance how);

    /* Report the stage due at now_ms (and whether it advanced). */
    EscalationDecision evaluate(long now_ms);

    /* Companion returned before L3 — cancel any pending stage (reversible). */
    void on_recovered();

    /* Operator override — cancel pending escalation. */
    void cancel();

    Stage current_stage() const;
    bool active() const; /* ladder running (absent, not cancelled) */

  private:
    EscalationConfig cfg_;
    bool active_;
    long base_ms_;     /* effective start (t0 + suspicious delay) */
    Stage last_stage_; /* last stage returned by evaluate */
};

} // namespace tether

#endif /* TETHER_ESCALATION_HPP */
