/* presence — PRESENT/FRINGE/ABSENT state machine (§3).
 *
 * RED STUB (Slice 1): tick() always returns PRESENT and updates no counters;
 * GREEN runs the FSM (threshold + consecutive-missed/recover tick counting). */
#include "presence.hpp"

namespace tether {

PresenceMachine::PresenceMachine(PresenceConfig cfg)
    : cfg_(cfg), state_(Presence::PRESENT), ticks_missed_(0), ticks_recovering_(0) {}

Presence PresenceMachine::tick(double smoothed_rssi, bool seen) {
    (void)smoothed_rssi; /* RED: GREEN compares against cfg_.near_threshold. */
    (void)seen;
    (void)cfg_;
    return Presence::PRESENT; /* RED sentinel */
}

Presence PresenceMachine::state() const { return state_; }
int PresenceMachine::ticks_missed() const { return ticks_missed_; }
int PresenceMachine::ticks_recovering() const { return ticks_recovering_; }

} // namespace tether
