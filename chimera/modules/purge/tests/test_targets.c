/* RED contract for the PURGE Tier-2 target registry (PR-1…PR-4). Fails against the stub
 * until GREEN. Pins: init, add+store, dedup by path, remove (idempotent), invalid/full
 * rejection, and the bridge that turns the registry into a dry-run plan. */
#include <stdio.h>

#include "unity.h"

#include "targets.h"

static void test_init_zero(void) {
    purge_targets_t r;
    r.count = 999;
    purge_targets_init(&r);
    TEST_ASSERT_EQUAL_INT(0, purge_target_count(&r));
}

static void test_add_stores(void) {
    purge_targets_t r = {0};
    purge_targets_init(&r);
    TEST_ASSERT_EQUAL_INT(1, purge_target_add(&r, "/vault/x", 1));
    TEST_ASSERT_EQUAL_INT(1, purge_target_count(&r));
    const purge_target_t *t = purge_target_at(&r, 0);
    TEST_ASSERT_NOT_NULL(t);
    TEST_ASSERT_EQUAL_STRING("/vault/x", t->path);
    TEST_ASSERT_EQUAL_INT(1, t->encrypted);
}

static void test_add_dedup_by_path(void) {
    purge_targets_t r = {0};
    purge_targets_init(&r);
    purge_target_add(&r, "/a", 0);
    purge_target_add(&r, "/a", 1); /* same path -> no dup, update encrypted */
    TEST_ASSERT_EQUAL_INT(1, purge_target_count(&r));
    const purge_target_t *t = purge_target_at(&r, 0);
    TEST_ASSERT_NOT_NULL(t);
    TEST_ASSERT_EQUAL_INT(1, t->encrypted);
}

static void test_add_multiple(void) {
    purge_targets_t r = {0};
    purge_targets_init(&r);
    purge_target_add(&r, "/a", 1);
    purge_target_add(&r, "/b", 0);
    TEST_ASSERT_EQUAL_INT(2, purge_target_count(&r));
}

static void test_remove(void) {
    purge_targets_t r = {0};
    purge_targets_init(&r);
    purge_target_add(&r, "/a", 1);
    purge_target_add(&r, "/b", 0);
    TEST_ASSERT_EQUAL_INT(1, purge_target_remove(&r, "/a"));
    TEST_ASSERT_EQUAL_INT(1, purge_target_count(&r));
    const purge_target_t *t = purge_target_at(&r, 0);
    TEST_ASSERT_NOT_NULL(t);
    TEST_ASSERT_EQUAL_STRING("/b", t->path);
}

static void test_remove_absent_idempotent(void) {
    purge_targets_t r = {0};
    purge_targets_init(&r);
    purge_target_add(&r, "/a", 1);
    TEST_ASSERT_EQUAL_INT(1, purge_target_remove(&r, "/nope")); /* unchanged */
    TEST_ASSERT_EQUAL_INT(1, purge_target_count(&r));
}

static void test_invalid_path_rejected(void) {
    purge_targets_t r = {0};
    purge_targets_init(&r);
    TEST_ASSERT_EQUAL_INT(-1, purge_target_add(&r, NULL, 1));
    TEST_ASSERT_EQUAL_INT(-1, purge_target_add(&r, "", 1));
    TEST_ASSERT_EQUAL_INT(0, purge_target_count(&r));
}

static void test_full_rejected(void) {
    purge_targets_t r = {0};
    purge_targets_init(&r);
    char path[32];
    for (int i = 0; i < PURGE_MAX_TARGETS; i++) {
        snprintf(path, sizeof(path), "/t%d", i);
        purge_target_add(&r, path, 0);
    }
    TEST_ASSERT_EQUAL_INT(PURGE_MAX_TARGETS, purge_target_count(&r));
    TEST_ASSERT_EQUAL_INT(-1, purge_target_add(&r, "/overflow", 0));
}

static void test_plan_bridge(void) {
    purge_targets_t r = {0};
    purge_targets_init(&r);
    purge_target_add(&r, "/a", 1);
    purge_target_add(&r, "/b", 0);
    purge_target_add(&r, "/c", 1);
    purge_plan_t p = purge_plan_targets(&r, 1, 1);
    TEST_ASSERT_EQUAL_INT(2, p.tier2_shred);
    TEST_ASSERT_EQUAL_INT(1, p.tier2_skip);
}

void run_targets_tests(void) {
    RUN_TEST(test_init_zero);
    RUN_TEST(test_add_stores);
    RUN_TEST(test_add_dedup_by_path);
    RUN_TEST(test_add_multiple);
    RUN_TEST(test_remove);
    RUN_TEST(test_remove_absent_idempotent);
    RUN_TEST(test_invalid_path_rejected);
    RUN_TEST(test_full_rejected);
    RUN_TEST(test_plan_bridge);
}
