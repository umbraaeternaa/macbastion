/* classify — disappearance classification FADE/CLEAN_DROP/INSTANT_DROP (§3). The
 * verdict is computed at the moment of loss (a seen→unseen transition):
 *   - a clean BLE disconnect flag             => CLEAN_DROP (benign)
 *   - the seen signal declined before loss    => FADE (operator walking away)
 *   - the seen signal was strong and stable,
 *     then vanished in one tick               => INSTANT_DROP (suspicious)
 * Conservative default is FADE — INSTANT_DROP fires only on a clearly strong,
 * non-declining signal, so noise biases toward normal (not delayed) escalation.
 * The thresholds are first-cut defaults (§9 calibration is an open question). */
#include "classify.hpp"

namespace tether {

namespace {
/* A decline of this many dBm across the recent window reads as a fade. */
constexpr double kFadeDeltaDb = 10.0;
/* A last-seen smoothed RSSI at or above this is "strong" (instant-drop gate). */
constexpr double kStrongDb = -60.0;
} // namespace

DisappearanceClassifier::DisappearanceClassifier()
    : recent_{}, count_(0), seen_prev_(false), clean_disconnect_(false),
      verdict_(Disappearance::NONE) {}

void DisappearanceClassifier::observe(double smoothed_rssi, bool seen, bool clean_disconnect) {
    if (seen) {
        recent_[count_ % kHistory] = smoothed_rssi;
        count_++;
        seen_prev_ = true;
        verdict_ = Disappearance::NONE; /* still present */
        return;
    }

    /* Not seen. Classify only at the transition into loss. */
    if (seen_prev_) {
        clean_disconnect_ = clean_disconnect;
        if (clean_disconnect) {
            verdict_ = Disappearance::CLEAN_DROP;
        } else if (count_ == 0) {
            verdict_ = Disappearance::FADE; /* no prior signal — treat as benign */
        } else {
            const int window = (count_ < kHistory) ? count_ : kHistory;
            const double last = recent_[(count_ - 1) % kHistory];
            double max = recent_[0];
            for (int i = 1; i < window; i++) {
                if (recent_[i] > max) {
                    max = recent_[i];
                }
            }
            if (max - last >= kFadeDeltaDb) {
                verdict_ = Disappearance::FADE; /* declined before vanishing */
            } else if (last >= kStrongDb) {
                verdict_ = Disappearance::INSTANT_DROP; /* strong, then gone in one tick */
            } else {
                verdict_ = Disappearance::FADE; /* weak/ambiguous — conservative */
            }
        }
    }
    seen_prev_ = false;
}

Disappearance DisappearanceClassifier::classify() const { return verdict_; }

void DisappearanceClassifier::reset() {
    count_ = 0;
    seen_prev_ = false;
    clean_disconnect_ = false;
    verdict_ = Disappearance::NONE;
}

} // namespace tether
