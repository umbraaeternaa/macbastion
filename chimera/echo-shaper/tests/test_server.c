/* A1 EP-5: the shaper's listening UNIX socket. Real AF_UNIX bind/connect/accept in one
 * process (connect completes via the listen backlog); hermetic — tmp path, no root. */
#include <stddef.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#include "unity.h"

#include "server.h"
#include "tests.h"

#define TEST_SOCK "/tmp/chimera_shaper_srv_test.sock"

static void test_listen_rejects_null(void) {
    TEST_ASSERT_EQUAL_INT(-1, shaper_server_listen(NULL));
}

static void test_listen_accept_roundtrip(void) {
    unlink(TEST_SOCK);
    int lfd = shaper_server_listen(TEST_SOCK);
    TEST_ASSERT_TRUE(lfd >= 0); /* bound + listening */

    int cfd = socket(AF_UNIX, SOCK_STREAM, 0);
    TEST_ASSERT_TRUE(cfd >= 0);
    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, TEST_SOCK, sizeof(addr.sun_path) - 1);
    TEST_ASSERT_EQUAL_INT(0, connect(cfd, (struct sockaddr *)&addr, sizeof(addr)));

    int conn = shaper_server_accept(lfd); /* served from the backlog */
    TEST_ASSERT_TRUE(conn >= 0);

    shaper_server_close(conn);
    shaper_server_close(cfd);
    shaper_server_close(lfd);
    unlink(TEST_SOCK);
}

void run_server_tests(void) {
    RUN_TEST(test_listen_rejects_null);
    RUN_TEST(test_listen_accept_roundtrip);
}
