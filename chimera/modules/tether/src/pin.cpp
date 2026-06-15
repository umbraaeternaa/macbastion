/* Companion pinning (anti-spoof). TOFU: the first device id seen is pinned (normalised);
 * thereafter only that exact device is trusted, and any other device advertising the same
 * service UUID is rejected — a fake beacon can no longer impersonate the companion. unpair()
 * forgets the pin so the next device re-pins (new phone). Pure + hermetic; the live scanner
 * feeds it the discovered device id. */
#include "pin.hpp"

#include "source.hpp" /* normalize_bt_addr */

namespace tether {

bool CompanionPin::accept(const std::string &device_id) {
    if (device_id.empty()) {
        return false; /* no device -> no presence (MANIFESTO §4) */
    }
    const std::string id = normalize_bt_addr(device_id);
    if (id.empty()) {
        return false;
    }
    if (pinned_.empty()) {
        pinned_ = id; /* TOFU — the first companion seen is bound */
        return true;
    }
    return id == pinned_; /* thereafter, only the pinned companion is trusted */
}

bool CompanionPin::paired() const {
    return !pinned_.empty();
}

std::string CompanionPin::pinned() const {
    return pinned_;
}

void CompanionPin::unpair() {
    pinned_.clear();
}

} // namespace tether
