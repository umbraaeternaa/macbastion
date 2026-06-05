/* Contract for the presence FSM (§3). RED: presence.cpp is stubbed (tick always
 * PRESENT, counters frozen at 0). PRESENT-state cases pass coincidentally; the
 * FRINGE/ABSENT/recovery/counter cases fail until GREEN runs the FSM. */
#include "unity.h"

#include "presence.hpp"

using tether::Presence;
using tether::PresenceConfig;
using tether::PresenceMachine;

static PresenceConfig cfg() {
    PresenceConfig c;
    c.near_threshold = -70.0;
    c.absent_ticks = 5;
    c.recover_ticks = 3;
    return c;
}

/* Coincidental-pass in RED (initial state is PRESENT anyway). */
static void test_starts_present(void) {
    PresenceMachine pm(cfg());
    TEST_ASSERT_EQUAL_INT(static_cast<int>(Presence::PRESENT), static_cast<int>(pm.state()));
}

static void test_weak_signal_goes_fringe(void) {
    PresenceMachine pm(cfg());
    Presence s = pm.tick(-85.0, true); /* below near_threshold */
    TEST_ASSERT_EQUAL_INT(static_cast<int>(Presence::FRINGE), static_cast<int>(s));
}

static void test_five_missed_ticks_absent(void) {
    PresenceMachine pm(cfg());
    Presence s = Presence::PRESENT;
    for (int i = 0; i < 5; i++) {
        s = pm.tick(0.0, false); /* not seen */
    }
    TEST_ASSERT_EQUAL_INT(static_cast<int>(Presence::ABSENT), static_cast<int>(s));
    TEST_ASSERT_EQUAL_INT(5, pm.ticks_missed());
}

static void test_ticks_missed_counts(void) {
    PresenceMachine pm(cfg());
    pm.tick(0.0, false);
    pm.tick(0.0, false);
    TEST_ASSERT_EQUAL_INT(2, pm.ticks_missed());
}

static void test_recovery_back_to_present(void) {
    PresenceMachine pm(cfg());
    for (int i = 0; i < 5; i++) {
        pm.tick(0.0, false); /* -> ABSENT */
    }
    Presence s = Presence::ABSENT;
    for (int i = 0; i < 3; i++) {
        s = pm.tick(-50.0, true); /* strong, seen -> recover */
    }
    TEST_ASSERT_EQUAL_INT(static_cast<int>(Presence::PRESENT), static_cast<int>(s));
}

static void test_strong_signal_stays_present(void) {
    PresenceMachine pm(cfg());
    TEST_ASSERT_EQUAL_INT(static_cast<int>(Presence::PRESENT),
                          static_cast<int>(pm.tick(-40.0, true)));
}

void run_presence_tests(void) {
    RUN_TEST(test_starts_present);
    RUN_TEST(test_weak_signal_goes_fringe);
    RUN_TEST(test_five_missed_ticks_absent);
    RUN_TEST(test_ticks_missed_counts);
    RUN_TEST(test_recovery_back_to_present);
    RUN_TEST(test_strong_signal_stays_present);
}
