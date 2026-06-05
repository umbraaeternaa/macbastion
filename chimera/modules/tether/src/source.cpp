/* source — RSSI sources. SyntheticSource (real test plumbing) replays a scripted
 * list. CoreBluetoothSource is the GATED real source (.mm later). make_source
 * picks between them by env — production gets the empty gated source and never
 * fabricates presence (§4). */
#include "source.hpp"

namespace tether {

bool SyntheticSource::next(Sample &out) {
    if (pos_ >= samples_.size()) {
        return false;
    }
    out = samples_[pos_++];
    return true;
}

bool CoreBluetoothSource::next(Sample &out) {
    (void)out; /* GATED: the .mm central scanner lands later; no sample yet. */
    return false;
}

std::unique_ptr<RssiSource> make_source() {
    /* RED: always the gated empty source. GREEN parses TETHER_SYNTHETIC_RSSI into
     * a SyntheticSource for the integration/dev path. */
    return std::unique_ptr<RssiSource>(new CoreBluetoothSource());
}

} // namespace tether
