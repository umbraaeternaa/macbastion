/* Contract for the escalation ladder (§3, EMIT-ONLY). RED: escalation.cpp is
 * stubbed (on_absent schedules nothing, evaluate always NONE, active stays
 * false). Pre-grace/NONE cases pass coincidentally; the timing/L3-gating/active
 * cases fail until GREEN. Deterministic via explicit now_ms (no real clock). */
#include "unity.h"

#include "escalation.hpp"

using tether::Disappearance;
using tether::EscalationConfig;
using tether::EscalationDecision;
using tether::EscalationLadder;
using tether::Stage;

static int as_int(Stage s) { return static_cast<int>(s); }

static EscalationConfig cfg(bool l3_armed) {
    EscalationConfig c;
    c.grace_ms = 30000;
    c.l1_to_l2_ms = 60000;
    c.l2_to_l3_ms = 300000;
    c.suspicious_delay_ms = 60000;
    c.l3_armed = l3_armed;
    return c;
}

/* Coincidental-pass in RED (nothing due at t0 anyway). */
static void test_no_stage_before_grace(void) {
    EscalationLadder l(cfg(false));
    l.on_absent(0, Disappearance::FADE);
    TEST_ASSERT_EQUAL_INT(as_int(Stage::NONE), as_int(l.evaluate(0).stage));
}

static void test_active_after_absent(void) {
    EscalationLadder l(cfg(false));
    l.on_absent(0, Disappearance::FADE);
    TEST_ASSERT_TRUE(l.active());
}

static void test_l1_after_grace(void) {
    EscalationLadder l(cfg(false));
    l.on_absent(0, Disappearance::FADE);
    TEST_ASSERT_EQUAL_INT(as_int(Stage::L1), as_int(l.evaluate(30000).stage));
}

static void test_l2_after_l1_delay(void) {
    EscalationLadder l(cfg(false));
    l.on_absent(0, Disappearance::FADE);
    TEST_ASSERT_EQUAL_INT(as_int(Stage::L2), as_int(l.evaluate(30000 + 60000).stage));
}

static void test_l3_when_armed(void) {
    EscalationLadder l(cfg(true));
    l.on_absent(0, Disappearance::FADE);
    TEST_ASSERT_EQUAL_INT(as_int(Stage::L3), as_int(l.evaluate(30000 + 60000 + 300000).stage));
}

static void test_l3_blocked_when_disarmed(void) {
    EscalationLadder l(cfg(false)); /* L3 opt-in, default disabled */
    l.on_absent(0, Disappearance::FADE);
    TEST_ASSERT_EQUAL_INT(as_int(Stage::L2), as_int(l.evaluate(30000 + 60000 + 300000).stage));
}

/* INSTANT_DROP shifts the schedule later by suspicious_delay (slows, never speeds). */
static void test_instant_drop_delays_l1(void) {
    EscalationLadder l(cfg(false));
    l.on_absent(0, Disappearance::INSTANT_DROP);
    TEST_ASSERT_EQUAL_INT(as_int(Stage::L1), as_int(l.evaluate(30000 + 60000).stage));
}

static void test_cancel_on_recovery(void) {
    EscalationLadder l(cfg(false));
    l.on_absent(0, Disappearance::FADE);
    l.on_recovered();
    TEST_ASSERT_FALSE(l.active());
}

void run_escalation_tests(void) {
    RUN_TEST(test_no_stage_before_grace);
    RUN_TEST(test_active_after_absent);
    RUN_TEST(test_l1_after_grace);
    RUN_TEST(test_l2_after_l1_delay);
    RUN_TEST(test_l3_when_armed);
    RUN_TEST(test_l3_blocked_when_disarmed);
    RUN_TEST(test_instant_drop_delays_l1);
    RUN_TEST(test_cancel_on_recovery);
}
