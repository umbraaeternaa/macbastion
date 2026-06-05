/* Contract for the Monitor (per-tick engine driver). RED: monitor.cpp's step()
 * returns no events, so every emit case fails; no-event-when-stable passes
 * coincidentally (empty == empty). Hermetic: synthetic Samples + explicit now_ms
 * (no real clock, no socket). The engine units are composed, never modified. */
#include "unity.h"

#include <vector>

#include "monitor.hpp"

using tether::Disappearance;
using tether::EscalationConfig;
using tether::EventKind;
using tether::Monitor;
using tether::MonitorEvent;
using tether::PresenceConfig;
using tether::Sample;
using tether::Stage;

static bool has_kind(const std::vector<MonitorEvent> &v, EventKind k) {
    for (const auto &e : v) {
        if (e.kind == k) {
            return true;
        }
    }
    return false;
}

static bool find_kind(const std::vector<MonitorEvent> &v, EventKind k, MonitorEvent &out) {
    for (const auto &e : v) {
        if (e.kind == k) {
            out = e;
            return true;
        }
    }
    return false;
}

static Monitor make_monitor(bool l3_armed = false) {
    PresenceConfig pc; /* near -70, absent 5, recover 3 */
    EscalationConfig ec; /* grace 30000, +60000, +300000, suspicious 60000 */
    Monitor m(pc, ec, 0.3);
    m.set_l3_armed(l3_armed);
    return m;
}

static Sample seen(double rssi) { return Sample{rssi, true, false}; }
static Sample missed() { return Sample{0.0, false, false}; }

static void test_fringe_on_weak_signal(void) {
    Monitor m = make_monitor();
    auto ev = m.step(seen(-85.0), 0); /* below near_threshold */
    TEST_ASSERT_TRUE(has_kind(ev, EventKind::FRINGE));
}

static void test_absent_after_five_missed(void) {
    Monitor m = make_monitor();
    std::vector<MonitorEvent> ev;
    for (int i = 0; i < 5; i++) {
        ev = m.step(missed(), 0);
    }
    TEST_ASSERT_TRUE(has_kind(ev, EventKind::ABSENT));
}

static void test_absent_carries_fade_class(void) {
    Monitor m = make_monitor();
    m.step(seen(-50.0), 0);
    m.step(seen(-70.0), 0);
    m.step(seen(-90.0), 0); /* steep decline */
    std::vector<MonitorEvent> ev;
    for (int i = 0; i < 5; i++) {
        ev = m.step(missed(), 0);
    }
    MonitorEvent e{};
    TEST_ASSERT_TRUE(find_kind(ev, EventKind::ABSENT, e));
    TEST_ASSERT_EQUAL_INT(static_cast<int>(Disappearance::FADE), static_cast<int>(e.how));
}

static void test_suspicious_on_instant_drop(void) {
    Monitor m = make_monitor();
    m.step(seen(-45.0), 0);
    m.step(seen(-44.0), 0); /* strong, stable */
    std::vector<MonitorEvent> ev;
    for (int i = 0; i < 5; i++) {
        ev = m.step(missed(), 0); /* vanished with no fade */
    }
    TEST_ASSERT_TRUE(has_kind(ev, EventKind::SUSPICIOUS));
}

static void test_escalation_l1_after_grace(void) {
    Monitor m = make_monitor();
    for (int i = 0; i < 5; i++) {
        m.step(missed(), 0); /* -> ABSENT, ladder armed at t0=0 */
    }
    auto ev = m.step(missed(), 30000); /* grace elapsed */
    MonitorEvent e{};
    TEST_ASSERT_TRUE(find_kind(ev, EventKind::ESCALATION, e));
    TEST_ASSERT_EQUAL_INT(static_cast<int>(Stage::L1), static_cast<int>(e.stage));
}

static void test_l3_blocked_when_disarmed(void) {
    Monitor m = make_monitor(false);
    for (int i = 0; i < 5; i++) {
        m.step(missed(), 0);
    }
    auto ev = m.step(missed(), 30000 + 60000 + 300000); /* past L3 time */
    MonitorEvent e{};
    TEST_ASSERT_TRUE(find_kind(ev, EventKind::ESCALATION, e));
    TEST_ASSERT_EQUAL_INT(static_cast<int>(Stage::L2), static_cast<int>(e.stage)); /* capped */
}

static void test_recovered_after_return(void) {
    Monitor m = make_monitor();
    for (int i = 0; i < 5; i++) {
        m.step(missed(), 0); /* -> ABSENT */
    }
    std::vector<MonitorEvent> ev;
    for (int i = 0; i < 3; i++) {
        ev = m.step(seen(-50.0), 1000); /* strong, recover_ticks */
    }
    TEST_ASSERT_TRUE(has_kind(ev, EventKind::RECOVERED));
}

static void test_present_from_fringe(void) {
    Monitor m = make_monitor();
    m.step(seen(-85.0), 0); /* weak -> FRINGE; smoothed = -85 */
    /* EWMA (alpha 0.3) smooths, so ONE strong tick after a weak one does not
     * cross near_threshold yet (-45 -> smoothed -73, still < -70 -> FRINGE).
     * A second strong tick accumulates over the threshold (-73 -> -64.6 >= -70)
     * -> PRESENT. This is the §3 spike-rejection feature, not a recovery bug. */
    m.step(seen(-45.0), 0); /* smoothed -73: still FRINGE */
    auto ev = m.step(seen(-45.0), 0); /* smoothed -64.6 >= -70 -> PRESENT */
    TEST_ASSERT_TRUE(has_kind(ev, EventKind::PRESENT));
}

/* Coincidental-pass in RED: a strong tick while PRESENT is no transition → no
 * event; the empty stub trivially matches. Real boundary in GREEN. */
static void test_no_event_when_stable(void) {
    Monitor m = make_monitor();
    auto ev = m.step(seen(-45.0), 0);
    TEST_ASSERT_EQUAL_INT(0, static_cast<int>(ev.size()));
}

void run_monitor_tests(void) {
    RUN_TEST(test_fringe_on_weak_signal);
    RUN_TEST(test_absent_after_five_missed);
    RUN_TEST(test_absent_carries_fade_class);
    RUN_TEST(test_suspicious_on_instant_drop);
    RUN_TEST(test_escalation_l1_after_grace);
    RUN_TEST(test_l3_blocked_when_disarmed);
    RUN_TEST(test_recovered_after_return);
    RUN_TEST(test_present_from_fringe);
    RUN_TEST(test_no_event_when_stable);
}
