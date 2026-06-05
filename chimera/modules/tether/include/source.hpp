/* RSSI source seam (TE-3). The presence engine consumes (rssi, seen,
 * clean_disconnect) samples per tick from an abstract source. The real source is
 * CoreBluetooth (an Objective-C++ .mm central scanner) — GATED on Bluetooth
 * hardware + TCC and absent this slice. Tests drive a SyntheticSource with a
 * scripted sample list, so the whole engine is hermetic. */
#ifndef TETHER_SOURCE_HPP
#define TETHER_SOURCE_HPP

#include <cstddef>
#include <memory>
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

/* The real BLE source — a CoreBluetooth (.mm) central scanner. GATED on Bluetooth
 * hardware + TCC; until the .mm lands it yields nothing (next() == false), so a
 * production daemon ticks but emits no presence — it NEVER fabricates presence
 * (MANIFESTO §4, the honest empty state, mirroring MIRROR's empty drain). */
class CoreBluetoothSource : public RssiSource {
  public:
    bool next(Sample &out) override;
};

/* Choose the daemon's source. With TETHER_SYNTHETIC_RSSI set (tests/dev only) →
 * a SyntheticSource from that script; otherwise → CoreBluetoothSource (the gated,
 * currently-empty production source). Production never sets the env. */
std::unique_ptr<RssiSource> make_source();

} // namespace tether

#endif /* TETHER_SOURCE_HPP */
