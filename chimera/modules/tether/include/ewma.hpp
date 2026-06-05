/* EWMA smoother for RSSI (§3: alpha 0.3, reject momentary spikes). First sample
 * initializes the average; subsequent samples blend alpha*sample + (1-alpha)*prev. */
#ifndef TETHER_EWMA_HPP
#define TETHER_EWMA_HPP

namespace tether {

class Ewma {
  public:
    explicit Ewma(double alpha);

    /* Fold one sample in; returns the new smoothed value. */
    double update(double sample);

    double value() const;
    bool initialized() const;
    void reset();

  private:
    double alpha_;
    double value_;
    bool initialized_;
};

} // namespace tether

#endif /* TETHER_EWMA_HPP */
