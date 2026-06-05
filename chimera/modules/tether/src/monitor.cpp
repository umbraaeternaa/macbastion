/* monitor — per-TICK engine driver.
 *
 * RED STUB (daemon-wiring Slice): step() returns no events; GREEN folds the
 * sample through EWMA → presence FSM → classify → escalation ladder and emits
 * the transition/escalation events. The engine units are composed here, never
 * modified. */
#include "monitor.hpp"

namespace tether {

Monitor::Monitor(PresenceConfig pc, EscalationConfig ec, double ewma_alpha)
    : ewma_(ewma_alpha), presence_(pc), classifier_(), ec_(ec), ladder_(ec),
      last_state_(Presence::PRESENT) {}

std::vector<MonitorEvent> Monitor::step(const Sample &sample, long now_ms) {
    (void)sample; /* RED: GREEN runs ewma_/presence_/classifier_/ladder_. */
    (void)now_ms;
    (void)ewma_;
    (void)presence_;
    (void)classifier_;
    (void)ec_;
    (void)ladder_;
    (void)last_state_;
    return {}; /* RED: no events emitted */
}

void Monitor::set_l3_armed(bool armed) { ec_.l3_armed = armed; }

Presence Monitor::state() const { return last_state_; }
double Monitor::rssi_smoothed() const { return ewma_.value(); }
Stage Monitor::stage() const { return ladder_.current_stage(); }

} // namespace tether
