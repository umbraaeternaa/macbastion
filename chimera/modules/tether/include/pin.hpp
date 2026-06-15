/* Companion pinning (anti-spoof, TE-pin). TETHER ranges by a BLE service UUID — but ANY
 * device advertising that UUID would otherwise count as "present", so a spoofer could hold
 * the Mac open (or pre-empt the dead-man) with a fake beacon. CompanionPin binds presence to
 * ONE device identity: TOFU — the first device id seen is pinned; thereafter only that exact
 * id is trusted, and a DIFFERENT id advertising the same UUID is rejected. unpair() forgets
 * the pin (new phone). Pure + hermetic: the live scanner feeds it the discovered device id.
 *
 * Persistence: with a non-empty state_path the pin is saved to that file and reloaded at
 * construction, so the bond SURVIVES a restart (a fresh beacon can't re-pin itself after a
 * tether respawn). An empty path keeps it in-memory only. */
#ifndef TETHER_PIN_HPP
#define TETHER_PIN_HPP

#include <string>

namespace tether {

class CompanionPin {
  public:
    /* state_path: file to persist the pin across restarts. Empty == in-memory only. If the
     * file exists at construction, the saved companion is loaded (survives restart). */
    explicit CompanionPin(std::string state_path = "");

    /* Observe a discovered device id; returns true iff it IS the trusted companion.
     * The first non-empty id seen pins (and persists, if a path is set); thereafter same id
     * -> true, any other -> false. An empty id never matches (no device -> no presence, §4). */
    bool accept(const std::string &device_id);
    bool paired() const;        /* a companion has been pinned */
    std::string pinned() const; /* the pinned (normalized) id, or "" when unpaired */
    void unpair();              /* forget the pin (in-memory + on-disk); the next device re-pins */

  private:
    std::string pinned_; /* normalized companion id; empty == unpaired */
    std::string path_;   /* persistence file; empty == no persistence */
    void load_();        /* read path_ -> pinned_ (if the file exists) */
    void save_() const;  /* write pinned_ -> path_ (if a path is set) */
};

} // namespace tether

#endif /* TETHER_PIN_HPP */
