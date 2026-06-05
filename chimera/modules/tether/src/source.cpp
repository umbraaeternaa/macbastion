/* source — SyntheticSource implementation (real test plumbing, the SS-7-style
 * seam). The real CoreBluetooth (.mm) source is GATED and lands later behind the
 * same RssiSource interface. */
#include "source.hpp"

namespace tether {

bool SyntheticSource::next(Sample &out) {
    if (pos_ >= samples_.size()) {
        return false;
    }
    out = samples_[pos_++];
    return true;
}

} // namespace tether
