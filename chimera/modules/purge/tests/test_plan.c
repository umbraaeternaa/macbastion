/* RED contract for the PURGE dry-run planner (PG-2/PG-3). Fails against the stub until
 * GREEN. Pins: §8 honest-wipe classification, always-on tier0/tier3, the refusal that an
 * unencrypted Tier-2 target is NEVER crypto-shredded, tier gating. Destroys nothing. */
#include "unity.h"

#include "plan.h"

static void test_classify_encrypted_shreds(void) {
    TEST_ASSERT_EQUAL_INT(PURGE_SHRED, purge_classify(1));
}

static void test_classify_unencrypted_skips(void) {
    TEST_ASSERT_EQUAL_INT(PURGE_SKIP_UNENCRYPTED, purge_classify(0));
}

static void test_default_plan_tier0_1_3(void) {
    purge_plan_t p = purge_build_plan(NULL, 0, 1, 0); /* tier1 on, tier2 off, no targets */
    TEST_ASSERT_EQUAL_INT(1, p.tier0);
    TEST_ASSERT_EQUAL_INT(1, p.tier1);
    TEST_ASSERT_EQUAL_INT(0, p.tier2_shred);
    TEST_ASSERT_EQUAL_INT(0, p.tier2_skip);
    TEST_ASSERT_EQUAL_INT(1, p.tier3);
}

static void test_tier2_mixed_counts(void) {
    int enc[] = {1, 0, 1}; /* enc, unenc, enc */
    purge_plan_t p = purge_build_plan(enc, 3, 1, 1);
    TEST_ASSERT_EQUAL_INT(2, p.tier2_shred);
    TEST_ASSERT_EQUAL_INT(1, p.tier2_skip);
}

static void test_tier2_disabled_ignores_targets(void) {
    int enc[] = {1, 1, 1};
    purge_plan_t p = purge_build_plan(enc, 3, 1, 0); /* tier2 off -> targets ignored */
    TEST_ASSERT_EQUAL_INT(0, p.tier2_shred);
    TEST_ASSERT_EQUAL_INT(0, p.tier2_skip);
}

static void test_tier1_disabled(void) {
    purge_plan_t p = purge_build_plan(NULL, 0, 0, 0);
    TEST_ASSERT_EQUAL_INT(0, p.tier1);
    TEST_ASSERT_EQUAL_INT(1, p.tier0); /* always-on */
    TEST_ASSERT_EQUAL_INT(1, p.tier3); /* always-on */
}

static void test_refusal_never_shreds_unencrypted(void) {
    int enc[] = {0, 0}; /* both unencrypted */
    purge_plan_t p = purge_build_plan(enc, 2, 1, 1);
    TEST_ASSERT_EQUAL_INT(0, p.tier2_shred); /* §8: never shred unencrypted */
    TEST_ASSERT_EQUAL_INT(2, p.tier2_skip);
}

void run_plan_tests(void) {
    RUN_TEST(test_classify_encrypted_shreds);
    RUN_TEST(test_classify_unencrypted_skips);
    RUN_TEST(test_default_plan_tier0_1_3);
    RUN_TEST(test_tier2_mixed_counts);
    RUN_TEST(test_tier2_disabled_ignores_targets);
    RUN_TEST(test_tier1_disabled);
    RUN_TEST(test_refusal_never_shreds_unencrypted);
}
