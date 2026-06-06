/* Contract for the evaluator (§3 step 3, §4): parse a known-good policy, evaluate
 * against an injected context. RED: vault_eval() returns VAULT_DENY, so ALLOW-case
 * tests fail and the DENY case passes coincidentally. Hermetic — context is supplied,
 * never gathered. */
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

static VaultVerdict ev(const char *text, const VaultContext *ctx) {
    char err[128];
    VaultPolicy *p = vault_parse(text, err, sizeof err);
    VaultVerdict v = vault_eval(p, ctx);
    vault_policy_free(p);
    return v;
}

static void test_eval_numeric_ge_allows(void) {
    VaultContext c = base_ctx();
    TEST_ASSERT_EQUAL_INT(VAULT_ALLOW, ev("allow_when: hour >= 9", &c));
}

/* Coincidental-pass in RED: an out-of-range hour must DENY. */
static void test_eval_numeric_out_of_range_denies(void) {
    VaultContext c = base_ctx();
    TEST_ASSERT_EQUAL_INT(VAULT_DENY, ev("allow_when: hour >= 20", &c));
}

static void test_eval_between(void) {
    VaultContext c = base_ctx();
    TEST_ASSERT_EQUAL_INT(VAULT_ALLOW, ev("allow_when: hour between 9 and 17", &c));
}

static void test_eval_enum_eq(void) {
    VaultContext c = base_ctx();
    TEST_ASSERT_EQUAL_INT(VAULT_ALLOW, ev("allow_when: pulse_mode == normal", &c));
}

static void test_eval_enum_in_list(void) {
    VaultContext c = base_ctx();
    TEST_ASSERT_EQUAL_INT(VAULT_ALLOW, ev("allow_when: weekday in [mon, wed, fri]", &c));
}

static void test_eval_string_eq(void) {
    VaultContext c = base_ctx();
    TEST_ASSERT_EQUAL_INT(VAULT_ALLOW, ev("allow_when: network_ssid == \"MyHomeWifi\"", &c));
}

static void test_eval_and_both_true(void) {
    VaultContext c = base_ctx();
    TEST_ASSERT_EQUAL_INT(VAULT_ALLOW,
                          ev("allow_when: hour >= 9 and pulse_mode == normal", &c));
}

static void test_eval_or_one_true(void) {
    VaultContext c = base_ctx();
    TEST_ASSERT_EQUAL_INT(VAULT_ALLOW,
                          ev("allow_when: hour >= 20 or tether == present", &c));
}

static void test_eval_not(void) {
    VaultContext c = base_ctx();
    TEST_ASSERT_EQUAL_INT(VAULT_ALLOW, ev("allow_when: not (hour >= 20)", &c));
}

void run_evaluator_tests(void) {
    RUN_TEST(test_eval_numeric_ge_allows);
    RUN_TEST(test_eval_numeric_out_of_range_denies);
    RUN_TEST(test_eval_between);
    RUN_TEST(test_eval_enum_eq);
    RUN_TEST(test_eval_enum_in_list);
    RUN_TEST(test_eval_string_eq);
    RUN_TEST(test_eval_and_both_true);
    RUN_TEST(test_eval_or_one_true);
    RUN_TEST(test_eval_not);
}
