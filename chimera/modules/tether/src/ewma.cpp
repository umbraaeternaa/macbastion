/* ewma — EWMA RSSI smoother (§3, alpha 0.3).
 *
 * RED STUB (Slice 1): update() returns a sentinel and does not blend; GREEN
 * implements alpha_*sample + (1-alpha_)*value_ with first-sample init. */
#include "ewma.hpp"

namespace tether {

Ewma::Ewma(double alpha) : alpha_(alpha), value_(0.0), initialized_(false) {}

double Ewma::update(double sample) {
    (void)sample; /* RED: GREEN blends alpha_*sample + (1-alpha_)*value_. */
    (void)alpha_;
    return 0.0; /* RED sentinel */
}

double Ewma::value() const { return value_; }
bool Ewma::initialized() const { return initialized_; }
void Ewma::reset() {
    initialized_ = false;
    value_ = 0.0;
}

} // namespace tether
