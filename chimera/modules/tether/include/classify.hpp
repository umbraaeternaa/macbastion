/* Disappearance classification (§3 anti-weaponization). Observes per-tick RSSI
 * and, at the moment the companion is lost, classifies HOW it vanished:
 *   FADE         — smoothed RSSI declined over several ticks before loss.
 *   CLEAN_DROP   — a clean BLE disconnect (Bluetooth off / battery) was signalled.
 *   INSTANT_DROP — strong last tick, gone this tick, no fade, no clean disconnect
 *                  => SUSPICIOUS (possible jamming): escalation is DELAYED.
 *   NONE         — still present / not lost.
 * This classification is the linchpin of L3 safety: a jammer slows the ladder,
 * never speeds it. */
#ifndef TETHER_CLASSIFY_HPP
#define TETHER_CLASSIFY_HPP

#include "tether.hpp"

namespace tether {

class DisappearanceClassifier {
  public:
    DisappearanceClassifier();

    /* Feed one tick of observation. */
    void observe(double smoothed_rssi, bool seen, bool clean_disconnect);

    /* Classify the most recent disappearance (NONE while still seen). */
    Disappearance classify() const;

    void reset();

  private:
    /* Small recent-history window to detect a fade vs an instant drop. */
    static constexpr int kHistory = 4;
    double recent_[kHistory];
    int count_;
    bool seen_prev_;
    bool clean_disconnect_;
    Disappearance verdict_;
};

} // namespace tether

#endif /* TETHER_CLASSIFY_HPP */
