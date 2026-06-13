/* A1 pf-anchor lifecycle: build the anchor rules (pure) + load/remove via an injectable
 * backend. Hermetic — a RECORDING backend captures every pf action; NO root, NO real pf. */
#include <stddef.h>
#include <stdio.h>
#include <string.h>

#include "unity.h"

#include "anchor.h"
#include "tests.h"

/* --- recording backend: capture each action as a string; optionally fail on a substring --- */
static char g_calls[16][256];
static int  g_ncalls;
static char g_fail_substr[64];

static void rec(const char *s) {
    if (g_ncalls < 16) {
        strncpy(g_calls[g_ncalls], s, 255);
        g_calls[g_ncalls][255] = '\0';
        g_ncalls++;
    }
}
static int rec_write_file(const char *path, const char *content) {
    char b[256];
    snprintf(b, sizeof b, "write %s :: %s", path, content);
    rec(b);
    return (g_fail_substr[0] && strstr(b, g_fail_substr)) ? -1 : 0;
}
static int rec_run(const char *const argv[]) {
    char b[256];
    size_t off = 0;
    off += (size_t)snprintf(b + off, sizeof b - off, "run");
    for (int i = 0; argv[i] != NULL && off < sizeof b; i++) {
        off += (size_t)snprintf(b + off, sizeof b - off, " %s", argv[i]);
    }
    rec(b);
    return (g_fail_substr[0] && strstr(b, g_fail_substr)) ? -1 : 0;
}
static int rec_remove_file(const char *path) {
    char b[256];
    snprintf(b, sizeof b, "remove %s", path);
    rec(b);
    return 0;
}
static const shaper_anchor_ops_t REC_OPS = {rec_write_file, rec_run, rec_remove_file};

static void rec_reset(const char *fail_substr) {
    g_ncalls = 0;
    for (int i = 0; i < 16; i++) {
        g_calls[i][0] = '\0';
    }
    g_fail_substr[0] = '\0';
    if (fail_substr != NULL) {
        strncpy(g_fail_substr, fail_substr, sizeof g_fail_substr - 1);
        g_fail_substr[sizeof g_fail_substr - 1] = '\0';
    }
    shaper_anchor_set_ops(&REC_OPS);
}

/* any recorded call contains substr? */
static int saw(const char *substr) {
    for (int i = 0; i < g_ncalls; i++) {
        if (strstr(g_calls[i], substr) != NULL) {
            return 1;
        }
    }
    return 0;
}

static void test_build_rules_routes_through_pipe(void) {
    char buf[128];
    TEST_ASSERT_EQUAL_INT(0, shaper_anchor_build_rules(buf, sizeof buf));
    TEST_ASSERT_NOT_NULL(strstr(buf, "dummynet"));
    TEST_ASSERT_NOT_NULL(strstr(buf, "pipe"));
}

static void test_build_rules_rejects_tiny_buffer(void) {
    char tiny[4];
    TEST_ASSERT_EQUAL_INT(-1, shaper_anchor_build_rules(tiny, sizeof tiny));
    TEST_ASSERT_EQUAL_INT(-1, shaper_anchor_build_rules(NULL, 128));
}

static void test_apply_runs_pipe_then_anchor(void) {
    rec_reset(NULL);
    TEST_ASSERT_EQUAL_INT(0, shaper_anchor_apply(100));
    TEST_ASSERT_TRUE(saw("write " SHAPER_ANCHOR_PATH)); /* anchor file written */
    TEST_ASSERT_TRUE(saw("dnctl"));                      /* pipe configured */
    TEST_ASSERT_TRUE(saw("100Kbit/s"));                  /* at the requested rate */
    TEST_ASSERT_TRUE(saw("pfctl"));                      /* anchor loaded */
    TEST_ASSERT_TRUE(saw(SHAPER_ANCHOR_NAME));
    rec_reset(NULL);
}

static void test_apply_rejects_bad_rate(void) {
    rec_reset(NULL);
    TEST_ASSERT_EQUAL_INT(-1, shaper_anchor_apply(0));
    TEST_ASSERT_EQUAL_INT(-1, shaper_anchor_apply(-5));
    TEST_ASSERT_EQUAL_INT(0, g_ncalls); /* nothing touched on a bad rate */
    rec_reset(NULL);
}

static void test_apply_propagates_failure(void) {
    rec_reset("dnctl"); /* make the pipe-config step fail */
    TEST_ASSERT_EQUAL_INT(-1, shaper_anchor_apply(100));
    rec_reset(NULL);
}

static void test_clear_is_failopen(void) {
    rec_reset("pfctl"); /* even if the flush fails... */
    TEST_ASSERT_EQUAL_INT(0, shaper_anchor_clear()); /* ...clear still returns 0 (fail-OPEN) */
    TEST_ASSERT_TRUE(saw("dnctl"));                   /* and still deletes the pipe */
    TEST_ASSERT_TRUE(saw("remove " SHAPER_ANCHOR_PATH)); /* and still removes the file */
    rec_reset(NULL);
}

void run_anchor_tests(void) {
    RUN_TEST(test_build_rules_routes_through_pipe);
    RUN_TEST(test_build_rules_rejects_tiny_buffer);
    RUN_TEST(test_apply_runs_pipe_then_anchor);
    RUN_TEST(test_apply_rejects_bad_rate);
    RUN_TEST(test_apply_propagates_failure);
    RUN_TEST(test_clear_is_failopen);
}
