/* Contract for LOCAL_PEERCRED auth (SS-6 / SH-5 (b)). RED: peercred.c's logic
 * (real getsockopt resolve + the uid predicate) is stubbed.
 *
 * Hermetic strategy (SS-7):
 *   - accept path: socketpair() gives a real connected UNIX pair; LOCAL_PEERCRED
 *     on it returns this process's own uid (real-fail in RED, real-pass in GREEN).
 *   - reject path: a mock resolver injected through the seam returns a wrong uid
 *     without needing a second process.
 * The resolver-swap seam itself is real plumbing → its test is green by design. */
#include "unity.h"

#include <sys/socket.h>
#include <unistd.h>

#include "peercred.h"
#include "shim.h"

#define MOCK_UID 4242u

static shim_result_t mock_resolver(int fd, shim_peer_t *out) {
    (void)fd;
    out->uid = (uid_t)MOCK_UID;
    out->gid = (gid_t)MOCK_UID;
    out->valid = 1;
    return SHIM_OK;
}

/* Predicate: matching operator uid is authorized. RED-fail (stub denies). */
static void test_authorized_uid_match(void) {
    shim_peer_t peer = {.uid = getuid(), .gid = getgid(), .valid = 1};
    TEST_ASSERT_EQUAL_INT(1, peercred_authorized(&peer, getuid()));
}

/* Coincidental-pass in RED (stub denies everything); real boundary in GREEN. */
static void test_authorized_wrong_uid_denied(void) {
    shim_peer_t peer = {.uid = getuid() + 1, .gid = getgid(), .valid = 1};
    TEST_ASSERT_EQUAL_INT(0, peercred_authorized(&peer, getuid()));
}

static void test_authorized_invalid_peer_denied(void) {
    shim_peer_t peer = {.uid = getuid(), .gid = getgid(), .valid = 0};
    TEST_ASSERT_EQUAL_INT(0, peercred_authorized(&peer, getuid()));
}

static void test_authorized_null_denied(void) {
    TEST_ASSERT_EQUAL_INT(0, peercred_authorized(NULL, getuid()));
}

/* Real LOCAL_PEERCRED over a socketpair — RED-fail (resolve stub errors). */
static void test_resolve_socketpair(void) {
    int sv[2];
    TEST_ASSERT_EQUAL_INT(0, socketpair(AF_UNIX, SOCK_STREAM, 0, sv));
    shim_peer_t peer = {0};
    shim_result_t rc = peercred_resolve_current(sv[0], &peer);
    close(sv[0]);
    close(sv[1]);
    TEST_ASSERT_EQUAL_INT(SHIM_OK, rc);
    TEST_ASSERT_EQUAL_INT(1, peer.valid);
    TEST_ASSERT_EQUAL_UINT(getuid(), peer.uid);
}

/* The injection seam itself (green by design — real plumbing, proves SS-7). */
static void test_resolver_seam_injects_mock(void) {
    peercred_resolver_fn prev = peercred_set_resolver(mock_resolver);
    shim_peer_t peer = {0};
    shim_result_t rc = peercred_resolve_current(7, &peer);
    peercred_set_resolver(prev);
    TEST_ASSERT_EQUAL_INT(SHIM_OK, rc);
    TEST_ASSERT_EQUAL_UINT(MOCK_UID, peer.uid);
}

void run_peercred_tests(void) {
    RUN_TEST(test_authorized_uid_match);
    RUN_TEST(test_authorized_wrong_uid_denied);
    RUN_TEST(test_authorized_invalid_peer_denied);
    RUN_TEST(test_authorized_null_denied);
    RUN_TEST(test_resolve_socketpair);
    RUN_TEST(test_resolver_seam_injects_mock);
}
