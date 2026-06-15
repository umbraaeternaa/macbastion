/* RSSI source seam (TE-3). The presence engine consumes (rssi, seen,
 * clean_disconnect) samples per tick from an abstract source. The real source is
 * CoreBluetooth (an Objective-C++ .mm central scanner) — GATED on Bluetooth
 * hardware + TCC and absent this slice. Tests drive a SyntheticSource with a
 * scripted sample list, so the whole engine is hermetic. */
#ifndef TETHER_SOURCE_HPP
#define TETHER_SOURCE_HPP

#include <cstddef>
#include <memory>
#include <string>
#include <vector>

#include "pin.hpp"

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

/* Live-feed source (TE-bridge): reads presence from a text file that an EXTERNAL,
 * already-Bluetooth-authorized scanner (the ble-probe tool) appends to. Each next()
 * parses the last line ("... PRESENT  rssi= -60 dBm ..." -> seen + rssi; "absent" ->
 * not seen). Lets the dead-man run on ble-probe's working Bluetooth grant when the
 * tether daemon itself is denied TCC (a bridge while the clean grant fix lands). */
class LiveFileSource : public RssiSource {
  public:
    explicit LiveFileSource(std::string path) : path_(std::move(path)) {}
    bool next(Sample &out) override;

  private:
    std::string path_;
};

/* The real BLE source — a CoreBluetooth (.mm) central scanner that ranges the
 * companion advertising `companion_id` (a BLE service UUID). Backed by cb_scanner.mm
 * (manual-tier: Bluetooth hardware + TCC). An empty companion_id, Bluetooth off, or a
 * denied grant all yield nothing (next() == false) — the daemon ticks but emits no
 * presence, NEVER fabricating it (MANIFESTO §4, the honest empty state). */
class CoreBluetoothSource : public RssiSource {
  public:
    /* Borrows the runtime's CompanionPin (ONE shared object) — so tether.unpair clears
     * THAT pin and the change bites this running source. An empty companion_id keeps the
     * scanner unstarted (no Bluetooth/TCC) → an honest empty source (§4). */
    CoreBluetoothSource(std::string companion_id, CompanionPin &pin, bool pin_enabled = true);
    ~CoreBluetoothSource() override;
    CoreBluetoothSource(const CoreBluetoothSource &) = delete;
    CoreBluetoothSource &operator=(const CoreBluetoothSource &) = delete;
    bool next(Sample &out) override;
    /* Live pin state (diagnostics/tests): is a companion currently bound? */
    bool pinned() const { return pin_.paired(); }

  private:
    void *scanner_;      /* opaque cb_scanner_t* (cb_scanner.mm); nullptr when unconfigured */
    CompanionPin &pin_;  /* anti-spoof: SHARED with the runtime (tether.unpair clears it) */
    bool pin_enabled_;   /* false for a RANDOM-ADDRESS companion (identity rotates, can't pin) */
};

/* Choose the daemon's source. With TETHER_SYNTHETIC_RSSI set (tests/dev only) →
 * a SyntheticSource from that script; otherwise → a CoreBluetoothSource ranging
 * `companion_id` and SHARING `pin` (the runtime's CompanionPin — so tether.unpair
 * resets the live source). Production never sets the env; an empty companion_id
 * keeps the source honestly empty (no companion configured → no presence). */
std::unique_ptr<RssiSource> make_source(const std::string &companion_id, CompanionPin &pin,
                                        bool pin_enabled = true);

/* Companion identity (TE-real). A BLE/Classic address as macOS reports it
 * ("A8:79:8D:90:1C:83"). normalize strips separators + lowercases so the same
 * device compares equal regardless of formatting. companion_matches returns true
 * iff a discovered device IS the configured companion; an empty config never
 * matches (no companion → never claim presence, MANIFESTO §4). Pure + hermetic. */
std::string normalize_bt_addr(const std::string &addr);
bool companion_matches(const std::string &configured, const std::string &device);

/* Presence decision (anti-spoof × random-address). Heard on the service UUID (scanner_seen) is
 * enough UNLESS pin_enabled — then the discovered identity must match the TOFU pin (anti-spoof
 * for stable-address companions). A random-address companion sets pin_enabled=false (its macOS
 * identifier rotates, so identity-pinning would reject it after each rotation). Pure + hermetic. */
bool resolve_seen(bool scanner_seen, bool pin_enabled, CompanionPin &pin, const std::string &device_id);

} // namespace tether

#endif /* TETHER_SOURCE_HPP */
