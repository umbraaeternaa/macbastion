/* classify — disappearance classification FADE/CLEAN_DROP/INSTANT_DROP (§3).
 *
 * RED STUB (Slice 1): observe() records history but classify() never computes a
 * verdict (stays NONE). GREEN derives FADE (gradual decline), CLEAN_DROP (clean
 * disconnect flag), INSTANT_DROP (strong→gone in one tick, no fade/clean). */
#include "classify.hpp"

namespace tether {

DisappearanceClassifier::DisappearanceClassifier()
    : recent_{}, count_(0), seen_prev_(false), clean_disconnect_(false),
      verdict_(Disappearance::NONE) {}

void DisappearanceClassifier::observe(double smoothed_rssi, bool seen, bool clean_disconnect) {
    /* RED: store the observation; do NOT classify (verdict_ stays NONE). */
    recent_[count_ % kHistory] = smoothed_rssi;
    count_++;
    seen_prev_ = seen;
    clean_disconnect_ = clean_disconnect;
}

Disappearance DisappearanceClassifier::classify() const {
    (void)recent_; /* RED: GREEN inspects the recent trend + flags. */
    (void)seen_prev_;
    (void)clean_disconnect_;
    return verdict_; /* RED: never set to a real verdict */
}

void DisappearanceClassifier::reset() {
    count_ = 0;
    verdict_ = Disappearance::NONE;
}

} // namespace tether
