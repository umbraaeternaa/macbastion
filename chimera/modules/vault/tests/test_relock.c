/* Contract for relock_after parsing (§4 duration). Slice 1 PARSES the duration; it
 * does NOT schedule a relock (that is the daemon/kqueue slice). RED: vault_parse()
 * returns NULL, so the duration tests fail; the absent case passes coincidentally. */
#include "unity.h"

#include "parser.h"

static VaultPolicy *parse(const char *text) {
    char err[128];
    return vault_parse(text, err, sizeof err);
}

static void test_relock_minutes(void) {
    VaultPolicy *p = parse("allow_when: hour >= 9\nrelock_after: 30min");
    TEST_ASSERT_NOT_NULL(p);
    long seconds = 0;
    TEST_ASSERT_TRUE(vault_policy_relock_seconds(p, &seconds));
    TEST_ASSERT_EQUAL_INT(1800, (int)seconds);
    vault_policy_free(p);
}

static void test_relock_hours(void) {
    VaultPolicy *p = parse("allow_when: hour >= 9\nrelock_after: 2hour");
    TEST_ASSERT_NOT_NULL(p);
    long seconds = 0;
    TEST_ASSERT_TRUE(vault_policy_relock_seconds(p, &seconds));
    TEST_ASSERT_EQUAL_INT(7200, (int)seconds);
    vault_policy_free(p);
}

/* Coincidental-pass in RED: no relock_after block -> accessor returns false. */
static void test_relock_absent_returns_false(void) {
    VaultPolicy *p = parse("allow_when: hour >= 9");
    long seconds = 0;
    TEST_ASSERT_FALSE(vault_policy_relock_seconds(p, &seconds));
    vault_policy_free(p);
}

void run_relock_tests(void) {
    RUN_TEST(test_relock_minutes);
    RUN_TEST(test_relock_hours);
    RUN_TEST(test_relock_absent_returns_false);
}
