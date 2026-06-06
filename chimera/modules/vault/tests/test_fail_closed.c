/* The SECURITY HEART of VAULT (§4 fail-closed): every uncertainty -> DENY. RED:
 * vault_policy_evaluate() returns DENY for everything, so the five DENY tests pass
 * coincidentally and the explicit-unknown-opt-in test (which must ALLOW) fails —
 * proving the suite is genuinely red on the one path that should open. */
#include "unity.h"

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

/* Coincidental-pass: an unparseable policy is never ALLOW. */
static void test_fc_parse_error_denies(void) {
    VaultContext c = base_ctx();
    TEST_ASSERT_EQUAL_INT(VAULT_DENY, vault_policy_evaluate("garbage }{ not valid", &c));
}

/* Coincidental-pass: a variable outside the whitelist is never ALLOW. */
static void test_fc_unknown_variable_denies(void) {
    VaultContext c = base_ctx();
    TEST_ASSERT_EQUAL_INT(VAULT_DENY, vault_policy_evaluate("allow_when: foobar == 1", &c));
}

/* Coincidental-pass: PULSE not running (UNKNOWN) + no opt-out -> DENY. */
static void test_fc_unknown_pulse_denies(void) {
    VaultContext c = base_ctx();
    c.pulse_mode = VPULSE_UNKNOWN;
    TEST_ASSERT_EQUAL_INT(VAULT_DENY, vault_policy_evaluate("allow_when: pulse_mode == normal", &c));
}

/* Coincidental-pass: ORACLE not running (oracle_known=false) -> DENY. */
static void test_fc_oracle_unknown_denies(void) {
    VaultContext c = base_ctx();
    c.oracle_known = false;
    TEST_ASSERT_EQUAL_INT(VAULT_DENY, vault_policy_evaluate("allow_when: oracle_score < 0.5", &c));
}

/* Coincidental-pass: comparing a numeric variable to an enum value is a type
 * mismatch -> DENY (not a silent true). */
static void test_fc_type_mismatch_denies(void) {
    VaultContext c = base_ctx();
    TEST_ASSERT_EQUAL_INT(VAULT_DENY, vault_policy_evaluate("allow_when: hour == mon", &c));
}

/* REAL-FAIL in RED: the explicit `unknown` opt-out MUST allow even when PULSE is
 * down. This is the one fail-closed test that should return ALLOW — the stub's
 * blanket DENY fails it, so GREEN must implement the opt-out correctly. */
static void test_fc_explicit_unknown_opt_in_allows(void) {
    VaultContext c = base_ctx();
    c.pulse_mode = VPULSE_UNKNOWN;
    TEST_ASSERT_EQUAL_INT(
        VAULT_ALLOW, vault_policy_evaluate("allow_when: pulse_mode in [normal, unknown]", &c));
}

void run_fail_closed_tests(void) {
    RUN_TEST(test_fc_parse_error_denies);
    RUN_TEST(test_fc_unknown_variable_denies);
    RUN_TEST(test_fc_unknown_pulse_denies);
    RUN_TEST(test_fc_oracle_unknown_denies);
    RUN_TEST(test_fc_type_mismatch_denies);
    RUN_TEST(test_fc_explicit_unknown_opt_in_allows);
}
