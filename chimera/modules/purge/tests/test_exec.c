/* PG-exec: the tier executor runs a plan's enabled tiers in key-first order via the seams.
 * Hermetic — counting stubs replace the no-op tier actions; nothing is destroyed. */
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "unity.h"

#include "exec.h"
#include "secrets.h"
#include "statefiles.h"
#include "targets.h"
#include "tests.h"

static int g_t0, g_t1, g_t3;
static int count_t0(void) {
    g_t0++;
    return 0;
}
static int count_t1(void) {
    g_t1++;
    return 0;
}
static int count_t3(void) {
    g_t3++;
    return 0;
}
static int fail_action(void) { return 1; }

static void inject_counting_seams(void) {
    g_t0 = g_t1 = g_t3 = 0;
    purge_set_tier0_action(count_t0);
    purge_set_tier1_action(count_t1);
    purge_set_tier3_action(count_t3);
}

static void reset_seams(void) {
    purge_set_tier0_action(NULL);
    purge_set_tier1_action(NULL);
    purge_set_tier2_action(NULL);
    purge_set_tier3_action(NULL);
}

/* plan fields: {tier0, tier1, tier2_shred, tier2_skip, tier3}. */

static void test_execute_runs_all_enabled_tiers(void) {
    inject_counting_seams();
    purge_plan_t plan = {1, 1, 3, 0, 1};
    purge_exec_result_t r = purge_execute(&plan, NULL); /* tier2 off — covered separately */
    TEST_ASSERT_EQUAL_INT(1, r.tier0_done);
    TEST_ASSERT_EQUAL_INT(1, r.tier1_done);
    TEST_ASSERT_EQUAL_INT(0, r.tier2_shred); /* no targets registry -> no tier2 effect */
    TEST_ASSERT_EQUAL_INT(1, r.tier3_done);
    TEST_ASSERT_EQUAL_INT(1, g_t0);
    TEST_ASSERT_EQUAL_INT(1, g_t1);
    TEST_ASSERT_EQUAL_INT(1, g_t3);
    reset_seams();
}

static void test_execute_skips_disabled_tier1(void) {
    inject_counting_seams();
    purge_plan_t plan = {1, 0, 0, 0, 1}; /* tier1 off */
    purge_exec_result_t r = purge_execute(&plan, NULL);
    TEST_ASSERT_EQUAL_INT(1, r.tier0_done);
    TEST_ASSERT_EQUAL_INT(0, r.tier1_done);
    TEST_ASSERT_EQUAL_INT(0, g_t1); /* tier1 action NOT invoked */
    TEST_ASSERT_EQUAL_INT(1, r.tier3_done);
    reset_seams();
}

static void test_execute_records_tier_failure(void) {
    inject_counting_seams();
    purge_set_tier1_action(fail_action); /* tier1 fails */
    purge_plan_t plan = {1, 1, 0, 0, 1};
    purge_exec_result_t r = purge_execute(&plan, NULL);
    TEST_ASSERT_EQUAL_INT(0, r.tier1_done); /* failure recorded */
    TEST_ASSERT_EQUAL_INT(1, r.tier0_done); /* other tiers still run */
    TEST_ASSERT_EQUAL_INT(1, r.tier3_done);
    reset_seams();
}

static void test_execute_null_plan_destroys_nothing(void) {
    inject_counting_seams();
    purge_exec_result_t r = purge_execute(NULL, NULL);
    TEST_ASSERT_EQUAL_INT(0, r.tier0_done);
    TEST_ASSERT_EQUAL_INT(0, r.tier3_done);
    TEST_ASSERT_EQUAL_INT(0, g_t0); /* no action invoked on a NULL plan */
    reset_seams();
}

/* Integration: with NO injected stub, the executor's REAL default tier3 action zeroes a
 * registered sensitive buffer in RAM — proves the secrets registry is wired into exec. */
static void test_execute_tier3_really_wipes_registered_ram(void) {
    reset_seams();        /* tier3 falls back to its real default (purge_secret_clear_all) */
    purge_secret_reset();
    unsigned char buf[48];
    memset(buf, 0xAA, sizeof buf);
    TEST_ASSERT_EQUAL_INT(0, purge_secret_register(buf, sizeof buf));
    purge_plan_t plan = {0, 0, 0, 0, 1}; /* tier3 only */
    purge_exec_result_t r = purge_execute(&plan, NULL);
    TEST_ASSERT_EQUAL_INT(1, r.tier3_done);
    for (size_t i = 0; i < sizeof buf; i++) {
        TEST_ASSERT_EQUAL_UINT8(0x00, buf[i]); /* tier3 zeroed real RAM */
    }
    purge_secret_reset();
}

/* Integration: with NO injected stub, the executor's REAL default tier0 action removes a
 * registered CHIMERA state file from disk (throwaway /tmp) — proves statefiles is wired in. */
static void test_execute_tier0_really_removes_registered_file(void) {
    reset_seams();        /* tier0 falls back to its real default (purge_statefile_remove_all) */
    purge_statefile_reset();
    const char *p = "/tmp/chimera_pg_exec_tier0.tmp";
    FILE *f = fopen(p, "w");
    if (f != NULL) {
        fputs("throwaway", f);
        fclose(f);
    }
    TEST_ASSERT_EQUAL_INT(0, access(p, F_OK)); /* exists now */
    TEST_ASSERT_EQUAL_INT(0, purge_statefile_register(p));
    purge_plan_t plan = {1, 0, 0, 0, 0}; /* tier0 only */
    purge_exec_result_t r = purge_execute(&plan, NULL);
    TEST_ASSERT_EQUAL_INT(1, r.tier0_done);
    TEST_ASSERT_EQUAL_INT(-1, access(p, F_OK)); /* tier0 deleted it from disk */
    purge_statefile_reset();
}

/* Integration: Tier-2 removes ENCRYPTED operator targets (real unlink) but REFUSES
 * unencrypted ones (§8 honest-wipe) — proves the executor's real tier2 over the registry. */
static void test_execute_tier2_shreds_encrypted_refuses_plain(void) {
    reset_seams(); /* tier2 uses its real default (unlink) */
    purge_targets_t targets;
    purge_targets_init(&targets);
    const char *enc = "/tmp/chimera_pg_tier2_enc.tmp";
    const char *plain = "/tmp/chimera_pg_tier2_plain.tmp";
    FILE *f = fopen(enc, "w");
    if (f != NULL) {
        fputs("x", f);
        fclose(f);
    }
    f = fopen(plain, "w");
    if (f != NULL) {
        fputs("x", f);
        fclose(f);
    }
    purge_target_add(&targets, enc, 1);   /* encrypted -> SHRED */
    purge_target_add(&targets, plain, 0); /* unencrypted -> REFUSE */
    purge_plan_t plan = purge_plan_targets(&targets, 1, 1);
    purge_exec_result_t r = purge_execute(&plan, &targets);
    TEST_ASSERT_EQUAL_INT(1, r.tier2_shred);       /* encrypted target removed */
    TEST_ASSERT_EQUAL_INT(1, r.tier2_skip);        /* unencrypted refused */
    TEST_ASSERT_EQUAL_INT(-1, access(enc, F_OK));  /* encrypted gone from disk */
    TEST_ASSERT_EQUAL_INT(0, access(plain, F_OK)); /* unencrypted UNTOUCHED (§8 honesty) */
    unlink(plain);                                 /* cleanup the refused file */
    reset_seams();
}

/* A NULL targets registry disables Tier-2 entirely — no shred, no skip. */
static void test_execute_tier2_null_targets_is_noop(void) {
    reset_seams();
    purge_plan_t plan = {0, 0, 0, 0, 0};
    purge_exec_result_t r = purge_execute(&plan, NULL);
    TEST_ASSERT_EQUAL_INT(0, r.tier2_shred);
    TEST_ASSERT_EQUAL_INT(0, r.tier2_skip);
    reset_seams();
}

void run_exec_tests(void) {
    RUN_TEST(test_execute_runs_all_enabled_tiers);
    RUN_TEST(test_execute_skips_disabled_tier1);
    RUN_TEST(test_execute_records_tier_failure);
    RUN_TEST(test_execute_null_plan_destroys_nothing);
    RUN_TEST(test_execute_tier3_really_wipes_registered_ram);
    RUN_TEST(test_execute_tier0_really_removes_registered_file);
    RUN_TEST(test_execute_tier2_shreds_encrypted_refuses_plain);
    RUN_TEST(test_execute_tier2_null_targets_is_noop);
}
