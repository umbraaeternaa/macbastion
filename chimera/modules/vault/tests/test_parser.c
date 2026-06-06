/* Contract for the recursive-descent parser (§4 grammar). RED: vault_parse()
 * returns NULL, so valid-policy tests fail; malformed/missing tests pass
 * coincidentally (NULL is the expected fail-closed result there). */
#include "unity.h"

#include "parser.h"

static VaultPolicy *parse(const char *text) {
    char err[128];
    return vault_parse(text, err, sizeof err);
}

static void test_parse_simple_and(void) {
    VaultPolicy *p = parse("allow_when: hour >= 9 and hour <= 17");
    TEST_ASSERT_NOT_NULL(p);
    vault_policy_free(p);
}

static void test_parse_not_or_parens(void) {
    VaultPolicy *p = parse("allow_when: not (tether == absent or pulse_mode == tired)");
    TEST_ASSERT_NOT_NULL(p);
    vault_policy_free(p);
}

static void test_parse_in_list_and_between(void) {
    VaultPolicy *p =
        parse("allow_when: weekday in [mon, tue, wed] and hour between 9 and 17");
    TEST_ASSERT_NOT_NULL(p);
    vault_policy_free(p);
}

static void test_parse_string_predicate(void) {
    VaultPolicy *p = parse("allow_when: network_ssid == \"MyHomeWifi\"");
    TEST_ASSERT_NOT_NULL(p);
    vault_policy_free(p);
}

/* Coincidental-pass in RED: a malformed operator must NOT parse (fail-closed). */
static void test_parse_malformed_returns_null(void) {
    TEST_ASSERT_NULL(parse("allow_when: hour >=>= 9"));
}

/* Coincidental-pass in RED: a policy with no allow_when block is invalid. */
static void test_parse_missing_allow_when_returns_null(void) {
    TEST_ASSERT_NULL(parse("hour >= 9"));
}

void run_parser_tests(void) {
    RUN_TEST(test_parse_simple_and);
    RUN_TEST(test_parse_not_or_parens);
    RUN_TEST(test_parse_in_list_and_between);
    RUN_TEST(test_parse_string_predicate);
    RUN_TEST(test_parse_malformed_returns_null);
    RUN_TEST(test_parse_missing_allow_when_returns_null);
}
