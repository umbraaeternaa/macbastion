/* C1 socket-ownership seam (mirrors shim SS-0(b)): the success path (chown to root) is
 * manual-tier/root-only; here we exercise the root-free failure paths — a NULL path, and the
 * EPERM a non-root caller hits trying to chown to root. */
#include <stddef.h>
#include <unistd.h>

#include "unity.h"

#include "ownership.h"
#include "shaper.h"
#include "tests.h"

static void test_ownership_rejects_null_path(void) {
    TEST_ASSERT_EQUAL_INT(SHAPER_ERR, shaper_ownership_apply(NULL, 20));
}

static void test_ownership_nonroot_cannot_chown_to_root(void) {
    /* A non-root process cannot chown a file to root — chown() returns EPERM, so the seam
     * returns SHAPER_ERR. (Ignored only in the unlikely case the suite itself runs as root.) */
    if (geteuid() == 0) {
        TEST_IGNORE_MESSAGE("running as root — the success path is manual-tier");
    }
    char path[] = "/tmp/chimera_shaper_own_test.XXXXXX";
    int fd = mkstemp(path);
    TEST_ASSERT_TRUE(fd >= 0);
    close(fd);
    TEST_ASSERT_EQUAL_INT(SHAPER_ERR, shaper_ownership_apply(path, 0));
    unlink(path);
}

void run_ownership_tests(void) {
    RUN_TEST(test_ownership_rejects_null_path);
    RUN_TEST(test_ownership_nonroot_cannot_chown_to_root);
}
