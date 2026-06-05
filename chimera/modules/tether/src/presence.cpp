/* presence — PRESENT/FRINGE/ABSENT state machine (§3). Fed one (smoothed_rssi,
 * seen) per tick: missed ticks drive PRESENT→FRINGE→ABSENT; a near signal seen
 * for recover_ticks ticks brings ABSENT back to PRESENT. */
#include "presence.hpp"

namespace tether {

PresenceMachine::PresenceMachine(PresenceConfig cfg)
    : cfg_(cfg), state_(Presence::PRESENT), ticks_missed_(0), ticks_recovering_(0) {}

Presence PresenceMachine::tick(double smoothed_rssi, bool seen) {
    if (!seen) {
        ticks_missed_++;
        ticks_recovering_ = 0;
        if (ticks_missed_ >= cfg_.absent_ticks) {
            state_ = Presence::ABSENT;
        } else if (state_ == Presence::PRESENT) {
            state_ = Presence::FRINGE; /* 1-2 missed: uncertain, no escalation yet */
        }
        return state_;
    }

    /* Seen this tick. */
    ticks_missed_ = 0;
    const bool near = smoothed_rssi >= cfg_.near_threshold;
    if (!near) {
        ticks_recovering_ = 0;
        if (state_ != Presence::ABSENT) {
            state_ = Presence::FRINGE; /* weak signal: fringe, but no recovery from ABSENT */
        }
        return state_;
    }

    /* Seen and near. */
    if (state_ == Presence::ABSENT) {
        ticks_recovering_++;
        if (ticks_recovering_ >= cfg_.recover_ticks) {
            state_ = Presence::PRESENT;
            ticks_recovering_ = 0;
        }
    } else {
        state_ = Presence::PRESENT;
        ticks_recovering_ = 0;
    }
    return state_;
}

Presence PresenceMachine::state() const { return state_; }
int PresenceMachine::ticks_missed() const { return ticks_missed_; }
int PresenceMachine::ticks_recovering() const { return ticks_recovering_; }

} // namespace tether
