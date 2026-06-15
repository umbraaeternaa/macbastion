/* Companion pinning (anti-spoof) + persistence.
 *
 * In-memory TOFU binds presence to ONE device identity (the first companion seen; any other
 * device on the same service UUID is rejected). With a non-empty state_path the bond is saved
 * to that file and reloaded at construction, so it SURVIVES a tether restart — a fresh beacon
 * cannot re-pin itself after a respawn. unpair() clears the bond in memory and on disk. The
 * id is normalised (normalize_bt_addr) so formatting never matters. */
#include "pin.hpp"

#include <cstdio>  /* std::remove */
#include <fstream> /* persistence I/O */

#include "source.hpp" /* normalize_bt_addr */

namespace tether {

CompanionPin::CompanionPin(std::string state_path) : path_(std::move(state_path)) {
    load_();
}

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
        save_();      /* persist the bond so it survives a restart */
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
    if (!path_.empty()) {
        std::remove(path_.c_str()); /* forget on disk too (NULL-safe no-op if absent) */
    }
}

void CompanionPin::load_() {
    if (path_.empty()) {
        return;
    }
    std::ifstream in(path_);
    if (!in) {
        return; /* no saved pin yet */
    }
    std::string id;
    in >> id; /* the saved (already-normalised) id; one token, no whitespace */
    if (!id.empty()) {
        pinned_ = id;
    }
}

void CompanionPin::save_() const {
    if (path_.empty()) {
        return;
    }
    std::ofstream out(path_, std::ios::trunc);
    if (out) {
        out << pinned_ << "\n";
    }
}

} // namespace tether
