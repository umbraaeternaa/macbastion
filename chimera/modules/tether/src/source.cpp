/* source — RSSI sources. SyntheticSource (real test plumbing) replays a scripted
 * list. CoreBluetoothSource is the GATED real source (.mm later). make_source
 * picks between them by env — production gets the empty gated source and never
 * fabricates presence (§4). */
#include "source.hpp"

#include <cctype>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>

#include "cJSON.h"

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
    /* Production (no env) → the gated CoreBluetooth source (empty until the .mm
     * lands); the daemon never fabricates presence (§4). Only when a test/dev
     * explicitly sets TETHER_SYNTHETIC_RSSI do we replay a scripted sequence.
     * Format: {"samples":[{"rssi":-50,"seen":true,"clean":false}, ...]}. */
    const char *path = std::getenv("TETHER_SYNTHETIC_RSSI");
    if (!path) {
        return std::unique_ptr<RssiSource>(new CoreBluetoothSource());
    }
    std::ifstream in(path);
    if (!in) {
        return std::unique_ptr<RssiSource>(new CoreBluetoothSource());
    }
    std::stringstream ss;
    ss << in.rdbuf();
    const std::string json = ss.str();

    cJSON *root = cJSON_Parse(json.c_str());
    if (!root) {
        return std::unique_ptr<RssiSource>(new CoreBluetoothSource());
    }
    std::vector<Sample> samples;
    cJSON *arr = cJSON_GetObjectItemCaseSensitive(root, "samples");
    if (cJSON_IsArray(arr)) {
        cJSON *item = nullptr;
        cJSON_ArrayForEach(item, arr) {
            Sample s{};
            cJSON *rssi = cJSON_GetObjectItemCaseSensitive(item, "rssi");
            cJSON *seen = cJSON_GetObjectItemCaseSensitive(item, "seen");
            cJSON *clean = cJSON_GetObjectItemCaseSensitive(item, "clean");
            s.rssi = cJSON_IsNumber(rssi) ? rssi->valuedouble : 0.0;
            s.seen = cJSON_IsTrue(seen);
            s.clean_disconnect = cJSON_IsTrue(clean);
            samples.push_back(s);
        }
    }
    cJSON_Delete(root);
    if (samples.empty()) {
        return std::unique_ptr<RssiSource>(new CoreBluetoothSource());
    }
    return std::unique_ptr<RssiSource>(new SyntheticSource(std::move(samples)));
}

/* Strip address separators (':' '-' and any whitespace) and lowercase, so the same
 * device compares equal however macOS / config formats it. */
std::string normalize_bt_addr(const std::string &addr) {
    std::string out;
    out.reserve(addr.size());
    for (char c : addr) {
        if (c == ':' || c == '-' || c == ' ' || c == '\t') {
            continue;
        }
        out.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(c))));
    }
    return out;
}

/* True iff the discovered device IS the configured companion. An unset companion or
 * an empty device id never matches — no companion → never claim presence (§4). */
bool companion_matches(const std::string &configured, const std::string &device) {
    if (configured.empty() || device.empty()) {
        return false;
    }
    return normalize_bt_addr(configured) == normalize_bt_addr(device);
}

} // namespace tether
