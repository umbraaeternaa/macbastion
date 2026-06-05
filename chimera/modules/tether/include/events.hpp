/* TETHER event payload builders (§6.6 events tether → core). Each returns a
 * malloc'd cJSON params object (caller owns; attach to a notification or delete).
 * EMIT-ONLY: tether.escalation requests a stage; it does not act. The disappearance
 * / stage enums are rendered to their wire strings here. */
#ifndef TETHER_EVENTS_HPP
#define TETHER_EVENTS_HPP

#include "cJSON.h"

#include "tether.hpp"

namespace tether {

/* Wire-string helpers (e.g. Stage::L1 -> "L1", Disappearance::FADE -> "fade"). */
const char *stage_name(Stage s);
const char *disappearance_name(Disappearance d);

/* {rssi_smoothed} */
cJSON *event_present(double rssi_smoothed);
/* {rssi_smoothed, ticks_missed} */
cJSON *event_fringe(double rssi_smoothed, int ticks_missed);
/* {since_ts, last_rssi, disappearance_class} */
cJSON *event_absent(long since_ts, double last_rssi, Disappearance how);
/* {stage, action_requested, grace_remaining} — EMIT-ONLY request, core acts */
cJSON *event_escalation(Stage stage, const char *action_requested, long grace_remaining_ms);
/* {at_stage, rssi_smoothed} */
cJSON *event_recovered(Stage at_stage, double rssi_smoothed);
/* {reason, escalation_delayed_by_sec} */
cJSON *event_suspicious(const char *reason, long delayed_by_sec);

} // namespace tether

#endif /* TETHER_EVENTS_HPP */
