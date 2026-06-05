/* Presence state machine (§3 steady state). Fed one (smoothed_rssi, seen) per
 * TICK; transitions PRESENT/FRINGE/ABSENT by signal strength and consecutive
 * missed ticks. Pure logic — the tick source (BLE) is injected upstream. */
#ifndef TETHER_PRESENCE_HPP
#define TETHER_PRESENCE_HPP

#include "tether.hpp"

namespace tether {

class PresenceMachine {
  public:
    explicit PresenceMachine(PresenceConfig cfg);

    /* Advance one tick. `seen` = companion resolved this tick; `smoothed_rssi`
     * is the EWMA output. Returns the resulting state. */
    Presence tick(double smoothed_rssi, bool seen);

    Presence state() const;
    int ticks_missed() const;     /* consecutive missed ticks */
    int ticks_recovering() const; /* consecutive near ticks while ABSENT */

  private:
    PresenceConfig cfg_;
    Presence state_;
    int ticks_missed_;
    int ticks_recovering_;
};

} // namespace tether

#endif /* TETHER_PRESENCE_HPP */
