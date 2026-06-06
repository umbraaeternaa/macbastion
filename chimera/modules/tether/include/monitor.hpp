/* Monitor — the per-TICK engine driver (daemon-wiring Slice). Composes the
 * Slice-1 engine units (Ewma + PresenceMachine + DisappearanceClassifier +
 * EscalationLadder) and, on each step(sample, now_ms), returns the events to
 * emit this tick as plain struct descriptors (NOT cJSON, NOT a socket) — so it
 * is hermetic and Unity-testable, exactly like the engine.
 *
 * The daemon owns the clock and the socket: it calls step() with a monotonic
 * now_ms and maps each MonitorEvent to a JSON-RPC notification via events.cpp.
 *
 * EMIT-ONLY (spec §5): a MonitorEvent of kind ESCALATION is a REQUEST for core
 * to act; the Monitor (and daemon) never lock/evict/reboot. The engine units are
 * UNCHANGED — Monitor is a layer on top. */
#ifndef TETHER_MONITOR_HPP
#define TETHER_MONITOR_HPP

#include <vector>

#include "classify.hpp"
#include "escalation.hpp"
#include "ewma.hpp"
#include "presence.hpp"
#include "source.hpp"
#include "tether.hpp"

namespace tether {

enum class EventKind { PRESENT, FRINGE, ABSENT, ESCALATION, RECOVERED, SUSPICIOUS };

/* Flat descriptor of one event to emit. Only the fields relevant to `kind` are
 * meaningful; the daemon maps it to the matching events.cpp payload builder. */
struct MonitorEvent {
    EventKind kind;
    double rssi_smoothed;    /* PRESENT / FRINGE / ABSENT(last) / RECOVERED */
    int ticks_missed;        /* FRINGE */
    Disappearance how;       /* ABSENT */
    Stage stage;             /* ESCALATION / RECOVERED(at_stage) */
    long grace_remaining_ms; /* ESCALATION */
    long delayed_by_sec;     /* SUSPICIOUS */
};

class Monitor {
  public:
    Monitor(PresenceConfig pc, EscalationConfig ec, double ewma_alpha);

    /* Advance one tick with a sample at monotonic now_ms; return events to emit. */
    std::vector<MonitorEvent> step(const Sample &sample, long now_ms);

    /* Live link to tether.l3.arm/disarm — gates whether the ladder reaches L3. */
    void set_l3_armed(bool armed);

    /* Live link to tether.heighten/relax — when set, the ladder re-arms with a
     * tighter (effective) grace so escalation is REQUESTED sooner. EMIT-ONLY is
     * unchanged; this only shifts timing, never adds an action. */
    void set_heightened(bool heightened);

    /* Snapshots for tether.status. */
    Presence state() const;
    double rssi_smoothed() const;
    Stage stage() const;

  private:
    Ewma ewma_;
    PresenceMachine presence_;
    DisappearanceClassifier classifier_;
    EscalationConfig ec_;       /* live config; set_l3_armed mutates l3_armed */
    EscalationLadder ladder_;   /* re-armed from ec_ at each ABSENT transition */
    Presence last_state_;
};

} // namespace tether

#endif /* TETHER_MONITOR_HPP */
