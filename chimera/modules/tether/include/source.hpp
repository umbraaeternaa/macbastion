/* RSSI source seam (TE-3). The presence engine consumes (rssi, seen,
 * clean_disconnect) samples per tick from an abstract source. The real source is
 * CoreBluetooth (an Objective-C++ .mm central scanner) — GATED on Bluetooth
 * hardware + TCC and absent this slice. Tests drive a SyntheticSource with a
 * scripted sample list, so the whole engine is hermetic. */
#ifndef TETHER_SOURCE_HPP
#define TETHER_SOURCE_HPP

#include <cstddef>
#include <vector>

namespace tether {

struct Sample {
    double rssi;           /* raw dBm */
    bool seen;             /* companion resolved this tick */
    bool clean_disconnect; /* a clean BLE disconnect was signalled this tick */
};

class RssiSource {
  public:
    virtual ~RssiSource() = default;
    /* Pull the next sample. Returns false when the source is exhausted. */
    virtual bool next(Sample &out) = 0;
};

/* Replays a scripted vector of samples — the hermetic test/standin source. */
class SyntheticSource : public RssiSource {
  public:
    explicit SyntheticSource(std::vector<Sample> samples)
        : samples_(std::move(samples)), pos_(0) {}
    bool next(Sample &out) override;

  private:
    std::vector<Sample> samples_;
    std::size_t pos_;
};

} // namespace tether

#endif /* TETHER_SOURCE_HPP */
