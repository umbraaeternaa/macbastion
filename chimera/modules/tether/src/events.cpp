/* events — TETHER event payload builders (§6.6). Each returns a malloc'd cJSON
 * params object (caller owns). EMIT-ONLY: tether.escalation requests a stage; it
 * does not act. Enums are rendered to their wire strings here. */
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

const char *presence_name(Presence p) {
    switch (p) {
    case Presence::PRESENT:
        return "present";
    case Presence::FRINGE:
        return "fringe";
    case Presence::ABSENT:
        return "absent";
    }
    return "present";
}

cJSON *event_present(double rssi_smoothed) {
    cJSON *o = cJSON_CreateObject();
    cJSON_AddNumberToObject(o, "rssi_smoothed", rssi_smoothed);
    return o;
}

cJSON *event_fringe(double rssi_smoothed, int ticks_missed) {
    cJSON *o = cJSON_CreateObject();
    cJSON_AddNumberToObject(o, "rssi_smoothed", rssi_smoothed);
    cJSON_AddNumberToObject(o, "ticks_missed", ticks_missed);
    return o;
}

cJSON *event_absent(long since_ts, double last_rssi, Disappearance how) {
    cJSON *o = cJSON_CreateObject();
    cJSON_AddNumberToObject(o, "since_ts", static_cast<double>(since_ts));
    cJSON_AddNumberToObject(o, "last_rssi", last_rssi);
    cJSON_AddStringToObject(o, "disappearance_class", disappearance_name(how));
    return o;
}

cJSON *event_escalation(Stage stage, const char *action_requested, long grace_remaining_ms) {
    cJSON *o = cJSON_CreateObject();
    cJSON_AddStringToObject(o, "stage", stage_name(stage));
    cJSON_AddStringToObject(o, "action_requested", action_requested ? action_requested : "");
    cJSON_AddNumberToObject(o, "grace_remaining", static_cast<double>(grace_remaining_ms));
    return o;
}

cJSON *event_recovered(Stage at_stage, double rssi_smoothed) {
    cJSON *o = cJSON_CreateObject();
    cJSON_AddStringToObject(o, "at_stage", stage_name(at_stage));
    cJSON_AddNumberToObject(o, "rssi_smoothed", rssi_smoothed);
    return o;
}

cJSON *event_suspicious(const char *reason, long delayed_by_sec) {
    cJSON *o = cJSON_CreateObject();
    cJSON_AddStringToObject(o, "reason", reason ? reason : "");
    cJSON_AddNumberToObject(o, "escalation_delayed_by_sec", static_cast<double>(delayed_by_sec));
    return o;
}

} // namespace tether
