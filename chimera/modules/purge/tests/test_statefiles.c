/* PG-statefiles: the CHIMERA-own-file registry + the real tier0 file-removal action.
 *   - registered throwaway files are actually unlink()ed by purge_statefile_remove_all;
 *   - an empty registry is a safe no-op;
 *   - register refuses NULL/empty/relative paths and caps at PURGE_STATEFILE_MAX.
 * Hermetic — only /tmp throwaway files this test creates; nothing of the operator's. */
#include <stddef.h>
#include <stdio.h>
#include <unistd.h>

#include "unity.h"

#include "statefiles.h"
#include "tests.h"

static void make_file(const char *path) {
    FILE *f = fopen(path, "w");
    if (f != NULL) {
        fputs("throwaway", f);
        fclose(f);
    }
}

static void test_register_then_remove_deletes_files(void) {
    purge_statefile_reset();
    const char *a = "/tmp/chimera_pg_tier0_a.tmp";
    const char *b = "/tmp/chimera_pg_tier0_b.tmp";
    make_file(a);
    make_file(b);
    TEST_ASSERT_EQUAL_INT(0, access(a, F_OK)); /* exist now */
    TEST_ASSERT_EQUAL_INT(0, access(b, F_OK));
    TEST_ASSERT_EQUAL_INT(0, purge_statefile_register(a));
    TEST_ASSERT_EQUAL_INT(0, purge_statefile_register(b));
    TEST_ASSERT_EQUAL_INT(2, (int)purge_statefile_count());
    TEST_ASSERT_EQUAL_INT(0, purge_statefile_remove_all());
    TEST_ASSERT_EQUAL_INT(-1, access(a, F_OK)); /* really gone from disk */
    TEST_ASSERT_EQUAL_INT(-1, access(b, F_OK));
    purge_statefile_reset();
}

static void test_register_refuses_bad_paths(void) {
    purge_statefile_reset();
    TEST_ASSERT_EQUAL_INT(-1, purge_statefile_register(NULL));
    TEST_ASSERT_EQUAL_INT(-1, purge_statefile_register(""));
    TEST_ASSERT_EQUAL_INT(-1, purge_statefile_register("relative/path")); /* not absolute */
    TEST_ASSERT_EQUAL_INT(0, (int)purge_statefile_count());
    purge_statefile_reset();
}

static void test_registry_caps_at_max(void) {
    purge_statefile_reset();
    char path[64];
    for (int i = 0; i < PURGE_STATEFILE_MAX; i++) {
        snprintf(path, sizeof path, "/tmp/chimera_pg_cap_%d", i);
        TEST_ASSERT_EQUAL_INT(0, purge_statefile_register(path)); /* fills the registry */
    }
    TEST_ASSERT_EQUAL_INT(-1, purge_statefile_register("/tmp/chimera_pg_overflow")); /* full */
    TEST_ASSERT_EQUAL_INT(PURGE_STATEFILE_MAX, (int)purge_statefile_count());
    purge_statefile_reset();
}

static void test_remove_all_empty_is_safe_noop(void) {
    purge_statefile_reset();
    TEST_ASSERT_EQUAL_INT(0, purge_statefile_remove_all()); /* nothing registered -> safe */
    purge_statefile_reset();
}

void run_statefiles_tests(void) {
    RUN_TEST(test_register_then_remove_deletes_files);
    RUN_TEST(test_register_refuses_bad_paths);
    RUN_TEST(test_registry_caps_at_max);
    RUN_TEST(test_remove_all_empty_is_safe_noop);
}
