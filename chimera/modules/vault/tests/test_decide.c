/* Contract for vault_decide (DEFER temporal projection). RED: vault_decide() is a
 * {DENY, 0} stub, so the ALLOW/DEFER tests fail; the DENY tests pass coincidentally.
 *
 * vault_eval (slice 1) is UNCHANGED — DEFER is a NEW path here, so the 30 slice-1
 * tests stay green. Hermetic: context is injected, projection holds non-time
 * variables constant (so a block time cannot lift -> DENY, never an endless DEFER). */
#include "unity.h"

#include "evaluator.h"
#include "parser.h"
#include "vault.h"

static VaultContext base_ctx(void) {
    VaultContext c;
    c.hour = 12;
    c.weekday = VWD_WED;
    c.day_of_month = 15;
    c.seconds_since_boot = 1000;
    c.pulse_mode = VPULSE_NORMAL;
    c.tether = VTETHER_PRESENT;
    c.network_ssid = "MyHomeWifi";
    c.oracle_score = 0.1;
    c.oracle_known = true;
    return c;
}

static VaultDecision decide(const char *text, const VaultContext *ctx) {
    char err[128];
    VaultPolicy *p = vault_parse(text, err, sizeof err);
    VaultDecision d = vault_decide(p, ctx);
    vault_policy_free(p);
    return d;
}

/* Allowed right now -> ALLOW, no wait. */
static void test_decide_allow_now(void) {
    VaultContext c = base_ctx(); /* hour 12 */
    VaultDecision d = decide("allow_when: hour between 9 and 17", &c);
    TEST_ASSERT_EQUAL_INT(VAULT_ALLOW, d.verdict);
    TEST_ASSERT_EQUAL_INT(0, (int)d.defer_seconds);
}

/* Blocked only by the hour -> DEFER until the next eligible hour (1h granularity). */
static void test_decide_defer_hour(void) {
    VaultContext c = base_ctx();
    c.hour = 8; /* one hour before the window opens */
    VaultDecision d = decide("allow_when: hour between 9 and 17", &c);
    TEST_ASSERT_EQUAL_INT(VAULT_DEFER, d.verdict);
    TEST_ASSERT_EQUAL_INT(3600, (int)d.defer_seconds);
}

/* Blocked by the weekday -> DEFER across days. Fri 12:00 -> Sat 00:00 = 12 hours. */
static void test_decide_defer_weekday(void) {
    VaultContext c = base_ctx();
    c.weekday = VWD_FRI;
    c.hour = 12;
    VaultDecision d = decide("allow_when: weekday in [sat, sun]", &c);
    TEST_ASSERT_EQUAL_INT(VAULT_DEFER, d.verdict);
    TEST_ASSERT_EQUAL_INT(12 * 3600, (int)d.defer_seconds);
}

/* Coincidental-pass in RED: a non-time block (tether absent) cannot be lifted by
 * advancing the clock -> DENY, never DEFER. */
static void test_decide_deny_nontime(void) {
    VaultContext c = base_ctx();
    c.tether = VTETHER_ABSENT;
    VaultDecision d = decide("allow_when: tether == present", &c);
    TEST_ASSERT_EQUAL_INT(VAULT_DENY, d.verdict);
    TEST_ASSERT_EQUAL_INT(0, (int)d.defer_seconds);
}

/* Coincidental-pass in RED: a base ERROR (type mismatch) is fail-closed -> DENY,
 * never projected into DEFER. */
static void test_decide_deny_error(void) {
    VaultContext c = base_ctx();
    VaultDecision d = decide("allow_when: hour == mon", &c); /* numeric var, enum value */
    TEST_ASSERT_EQUAL_INT(VAULT_DENY, d.verdict);
    TEST_ASSERT_EQUAL_INT(0, (int)d.defer_seconds);
}

/* Coincidental-pass in RED: a policy that is never TRUE within the 7-day cap (here
 * never at all) -> DENY. */
static void test_decide_deny_cap(void) {
    VaultContext c = base_ctx();
    VaultDecision d = decide("allow_when: hour >= 25", &c); /* impossible: hour <= 23 */
    TEST_ASSERT_EQUAL_INT(VAULT_DENY, d.verdict);
    TEST_ASSERT_EQUAL_INT(0, (int)d.defer_seconds);
}

/* Composite: hour-block is time-liftable, tether-block is not. */
static void test_decide_composite(void) {
    /* tether present, only the hour blocks -> DEFER 1h */
    VaultContext a = base_ctx();
    a.hour = 8;
    a.tether = VTETHER_PRESENT;
    VaultDecision da =
        decide("allow_when: hour between 9 and 17 and tether == present", &a);
    TEST_ASSERT_EQUAL_INT(VAULT_DEFER, da.verdict);
    TEST_ASSERT_EQUAL_INT(3600, (int)da.defer_seconds);

    /* tether absent -> time cannot lift it -> DENY */
    VaultContext b = base_ctx();
    b.hour = 8;
    b.tether = VTETHER_ABSENT;
    VaultDecision db =
        decide("allow_when: hour between 9 and 17 and tether == present", &b);
    TEST_ASSERT_EQUAL_INT(VAULT_DENY, db.verdict);
}

void run_decide_tests(void) {
    RUN_TEST(test_decide_allow_now);
    RUN_TEST(test_decide_defer_hour);
    RUN_TEST(test_decide_defer_weekday);
    RUN_TEST(test_decide_deny_nontime);
    RUN_TEST(test_decide_deny_error);
    RUN_TEST(test_decide_deny_cap);
    RUN_TEST(test_decide_composite);
}
