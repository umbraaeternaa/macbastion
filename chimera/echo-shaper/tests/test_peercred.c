/* A1 EP-5: peer-credential auth. The accept path uses a REAL socketpair (resolves our own
 * uid); the reject path uses a mock resolver. Hermetic — no second process, no root. */
#include <stddef.h>
#include <sys/socket.h>
#include <unistd.h>

#include "unity.h"

#include "peercred.h"
#include "tests.h"

static void test_authorized_predicate(void) {
    shaper_peer_t ok = {.uid = 501, .gid = 20, .valid = 1};
    TEST_ASSERT_EQUAL_INT(1, shaper_peercred_authorized(&ok, 501));
    TEST_ASSERT_EQUAL_INT(0, shaper_peercred_authorized(&ok, 502)); /* wrong uid */
    shaper_peer_t invalid = {.uid = 501, .gid = 20, .valid = 0};
    TEST_ASSERT_EQUAL_INT(0, shaper_peercred_authorized(&invalid, 501)); /* unresolved */
    TEST_ASSERT_EQUAL_INT(0, shaper_peercred_authorized(NULL, 501));     /* deny-by-default */
}

static void test_resolve_real_socketpair(void) {
    shaper_peercred_set_resolver(NULL); /* the real getsockopt resolver */
    int sv[2];
    TEST_ASSERT_EQUAL_INT(0, socketpair(AF_UNIX, SOCK_STREAM, 0, sv));
    shaper_peer_t p;
    TEST_ASSERT_EQUAL_INT(SHAPER_OK, shaper_peercred_resolve_current(sv[0], &p));
    TEST_ASSERT_EQUAL_INT(1, p.valid);
    TEST_ASSERT_EQUAL_INT((int)getuid(), (int)p.uid);            /* our own creds */
    TEST_ASSERT_EQUAL_INT(1, shaper_peercred_authorized(&p, getuid()));
    TEST_ASSERT_EQUAL_INT(0, shaper_peercred_authorized(&p, getuid() + 1));
    close(sv[0]);
    close(sv[1]);
}

static shaper_result_t mock_resolver(int fd, shaper_peer_t *out) {
    (void)fd;
    out->uid = 4242;
    out->gid = 0;
    out->valid = 1;
    return SHAPER_OK;
}

static void test_resolver_seam_reject(void) {
    shaper_peercred_set_resolver(mock_resolver);
    shaper_peer_t p;
    TEST_ASSERT_EQUAL_INT(SHAPER_OK, shaper_peercred_resolve_current(-1, &p));
    TEST_ASSERT_EQUAL_INT(4242, (int)p.uid);
    TEST_ASSERT_EQUAL_INT(0, shaper_peercred_authorized(&p, getuid())); /* 4242 != us -> reject */
    shaper_peercred_set_resolver(NULL);                                  /* restore default */
}

void run_peercred_tests(void) {
    RUN_TEST(test_authorized_predicate);
    RUN_TEST(test_resolve_real_socketpair);
    RUN_TEST(test_resolver_seam_reject);
}
