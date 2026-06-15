/* Companion pinning (anti-spoof, TE-pin). TETHER ranges by a BLE service UUID — but ANY
 * device advertising that UUID would otherwise count as "present", so a spoofer could hold
 * the Mac open (or pre-empt the dead-man) with a fake beacon. CompanionPin binds presence to
 * ONE device identity: TOFU — the first device id seen is pinned; thereafter only that exact
 * id is trusted, and a DIFFERENT id advertising the same UUID is rejected. unpair() forgets
 * the pin (new phone). Pure + hermetic: the live scanner feeds it the discovered device id. */
#ifndef TETHER_PIN_HPP
#define TETHER_PIN_HPP

#include <string>

namespace tether {

class CompanionPin {
  public:
    /* Observe a discovered device id; returns true iff it IS the trusted companion.
     * The first non-empty id seen pins; thereafter same id -> true, any other -> false.
     * An empty id never matches (no device -> no presence, MANIFESTO §4). */
    bool accept(const std::string &device_id);
    bool paired() const;        /* a companion has been pinned */
    std::string pinned() const; /* the pinned (normalized) id, or "" when unpaired */
    void unpair();              /* forget the pin; the next device re-pins */

  private:
    std::string pinned_; /* normalized companion id; empty == unpaired */
};

} // namespace tether

#endif /* TETHER_PIN_HPP */
