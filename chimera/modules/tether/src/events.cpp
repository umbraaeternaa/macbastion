/* events — TETHER event payload builders (§6.6).
 *
 * RED STUB (Slice 1): the wire-string helpers (stage_name/disappearance_name) are
 * REAL (pure mappings, like ops_method_name); the cJSON payload builders are
 * stubbed to nullptr. GREEN builds the objects via cJSON. */
#include "events.hpp"

namespace tether {

const char *stage_name(Stage s) {
    switch (s) {
    case Stage::L1:
        return "L1";
    case Stage::L2:
        return "L2";
    case Stage::L3:
        return "L3";
    case Stage::NONE:
        return "none";
    }
    return "none";
}

const char *disappearance_name(Disappearance d) {
    switch (d) {
    case Disappearance::FADE:
        return "fade";
    case Disappearance::CLEAN_DROP:
        return "clean_drop";
    case Disappearance::INSTANT_DROP:
        return "instant_drop";
    case Disappearance::NONE:
        return "none";
    }
    return "none";
}

/* RED: payload builders not implemented (GREEN builds the cJSON params). */
cJSON *event_present(double rssi_smoothed) {
    (void)rssi_smoothed;
    return nullptr;
}

cJSON *event_fringe(double rssi_smoothed, int ticks_missed) {
    (void)rssi_smoothed;
    (void)ticks_missed;
    return nullptr;
}

cJSON *event_absent(long since_ts, double last_rssi, Disappearance how) {
    (void)since_ts;
    (void)last_rssi;
    (void)how;
    return nullptr;
}

cJSON *event_escalation(Stage stage, const char *action_requested, long grace_remaining_ms) {
    (void)stage;
    (void)action_requested;
    (void)grace_remaining_ms;
    return nullptr;
}

cJSON *event_recovered(Stage at_stage, double rssi_smoothed) {
    (void)at_stage;
    (void)rssi_smoothed;
    return nullptr;
}

cJSON *event_suspicious(const char *reason, long delayed_by_sec) {
    (void)reason;
    (void)delayed_by_sec;
    return nullptr;
}

} // namespace tether
