/* Contract for the listening server socket (SH-2). RED: server.c is stubbed, so
 * server_listen returns -1 and binds nothing. Hermetic: bind under a tmp path
 * (SS-7, configurable path) — no root, no /var/run. Full accept()/client round
 * trip is exercised under the manual `-m privileged` tier (needs a connecting
 * client); here we assert the bind + socket-file creation. */
#include "unity.h"

#include <sys/stat.h>
#include <unistd.h>

#include "server.h"
#include "shim.h"

#define TEST_SOCK_PATH "/tmp/chimera-shim-test.sock"

static void test_listen_binds_and_creates_file(void) {
    unlink(TEST_SOCK_PATH);
    int fd = server_listen(TEST_SOCK_PATH);
    TEST_ASSERT_TRUE(fd >= 0);

    struct stat st;
    int existed = (stat(TEST_SOCK_PATH, &st) == 0);

    server_close(fd);
    unlink(TEST_SOCK_PATH);
    TEST_ASSERT_TRUE(existed);
}

/* Coincidental-pass in RED (stub returns -1 for everything); real boundary in
 * GREEN where a valid path succeeds and only NULL fails. */
static void test_listen_null_path_fails(void) {
    TEST_ASSERT_EQUAL_INT(-1, server_listen(NULL));
}

void run_server_tests(void) {
    RUN_TEST(test_listen_binds_and_creates_file);
    RUN_TEST(test_listen_null_path_fails);
}
