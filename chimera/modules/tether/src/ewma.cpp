/* ewma — EWMA RSSI smoother (§3, alpha 0.3). The first sample initializes the
 * average; subsequent samples blend alpha_*sample + (1-alpha_)*value_, rejecting
 * momentary spikes. */
#include "ewma.hpp"

namespace tether {

Ewma::Ewma(double alpha) : alpha_(alpha), value_(0.0), initialized_(false) {}

double Ewma::update(double sample) {
    if (!initialized_) {
        value_ = sample;
        initialized_ = true;
    } else {
        value_ = alpha_ * sample + (1.0 - alpha_) * value_;
    }
    return value_;
}

double Ewma::value() const { return value_; }
bool Ewma::initialized() const { return initialized_; }
void Ewma::reset() {
    initialized_ = false;
    value_ = 0.0;
}

} // namespace tether
