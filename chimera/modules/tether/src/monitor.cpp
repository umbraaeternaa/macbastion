/* monitor — per-TICK engine driver. Folds one sample through EWMA → presence
 * FSM → disappearance classify → escalation ladder, returning the events to emit
 * this tick as struct descriptors. Composes the engine units; never modifies them.
 *
 * EMIT-ONLY (spec §5): an ESCALATION descriptor is a REQUEST for core to act;
 * the Monitor never locks/evicts/reboots. */
#include "monitor.hpp"

namespace tether {

Monitor::Monitor(PresenceConfig pc, EscalationConfig ec, double ewma_alpha)
    : ewma_(ewma_alpha), presence_(pc), classifier_(), ec_(ec), ladder_(ec),
      last_state_(Presence::PRESENT) {}

std::vector<MonitorEvent> Monitor::step(const Sample &sample, long now_ms) {
    std::vector<MonitorEvent> events;

    /* 1. Smooth (only seen ticks carry a new RSSI; missed ticks keep the last). */
    const double smoothed = sample.seen ? ewma_.update(sample.rssi) : ewma_.value();

    /* 2. Feed the classifier every tick (it derives the loss verdict at the
     *    seen→unseen transition). */
    classifier_.observe(smoothed, sample.seen, sample.clean_disconnect);

    /* 3. Advance the presence FSM; detect a state transition. */
    const Presence prev = last_state_;
    const Presence now = presence_.tick(smoothed, sample.seen);
    last_state_ = now;

    if (now != prev) {
        if (now == Presence::FRINGE) {
            MonitorEvent e{};
            e.kind = EventKind::FRINGE;
            e.rssi_smoothed = smoothed;
            e.ticks_missed = presence_.ticks_missed();
            events.push_back(e);
        } else if (now == Presence::ABSENT) {
            const Disappearance how = classifier_.classify();
            MonitorEvent a{};
            a.kind = EventKind::ABSENT;
            a.rssi_smoothed = smoothed;
            a.how = how;
            events.push_back(a);
            if (how == Disappearance::INSTANT_DROP) {
                MonitorEvent s{};
                s.kind = EventKind::SUSPICIOUS;
                s.delayed_by_sec = ec_.suspicious_delay_ms / 1000;
                events.push_back(s);
            }
            /* Arm a fresh ladder from the current config (picks up l3_armed). */
            ladder_ = EscalationLadder(ec_);
            ladder_.on_absent(now_ms, how);
        } else { /* now == PRESENT */
            if (prev == Presence::ABSENT) {
                MonitorEvent r{};
                r.kind = EventKind::RECOVERED;
                r.stage = ladder_.current_stage();
                r.rssi_smoothed = smoothed;
                events.push_back(r);
                ladder_.on_recovered();
            } else {
                MonitorEvent p{};
                p.kind = EventKind::PRESENT;
                p.rssi_smoothed = smoothed;
                events.push_back(p);
            }
        }
    }

    /* 4. While absent, advance the escalation ladder; emit on stage change. */
    if (now == Presence::ABSENT && ladder_.active()) {
        const EscalationDecision d = ladder_.evaluate(now_ms);
        if (d.changed && d.stage != Stage::NONE) {
            MonitorEvent e{};
            e.kind = EventKind::ESCALATION;
            e.stage = d.stage;
            e.grace_remaining_ms = d.grace_remaining_ms;
            events.push_back(e);
        }
    }

    return events;
}

void Monitor::set_l3_armed(bool armed) { ec_.l3_armed = armed; }

Presence Monitor::state() const { return last_state_; }
double Monitor::rssi_smoothed() const { return ewma_.value(); }
Stage Monitor::stage() const { return ladder_.current_stage(); }

} // namespace tether
