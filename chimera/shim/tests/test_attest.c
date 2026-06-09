/* Attestation fail-closed contract (2b-ii). The POSITIVE path — the real signed core
 * satisfies its designated requirement -> 1 — is manual-tier (verified live via the
 * `-m privileged` shim against the installed signed core; an unsigned test process cannot
 * stand in for it). These hermetic tests pin the fail-closed seams: NULL requirement, an fd
 * with no peer audit token, and a real AF_UNIX peer (this unsigned test process) that does
 * NOT satisfy a specific identifier. RED: attest.c returns 1 (fail-open) -> all three fail. */
#include "unity.h"

#include <sys/socket.h>
#include <unistd.h>

#include "attest.h"

static void test_null_requirement_denied(void) {
    int sv[2];
    TEST_ASSERT_EQUAL_INT(0, socketpair(AF_UNIX, SOCK_STREAM, 0, sv));
    TEST_ASSERT_EQUAL_INT(0, attest_peer_is_core(sv[0], NULL));
    close(sv[0]);
    close(sv[1]);
}

static void test_bad_fd_denied(void) {
    /* -1 is not a socket: no peer audit token -> fail-closed. */
    TEST_ASSERT_EQUAL_INT(0, attest_peer_is_core(-1, "anchor apple"));
}

static void test_nonmatching_requirement_denied(void) {
    /* A real AF_UNIX peer (this unsigned test process) does not satisfy this identifier. */
    int sv[2];
    TEST_ASSERT_EQUAL_INT(0, socketpair(AF_UNIX, SOCK_STREAM, 0, sv));
    TEST_ASSERT_EQUAL_INT(0, attest_peer_is_core(sv[0], "identifier \"com.chimera.definitely.not\""));
    close(sv[0]);
    close(sv[1]);
}

void run_attest_tests(void) {
    RUN_TEST(test_null_requirement_denied);
    RUN_TEST(test_bad_fd_denied);
    RUN_TEST(test_nonmatching_requirement_denied);
}
