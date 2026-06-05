/* server — privileged-shim listening UNIX socket (SH-2). SERVER side.
 *
 * RED STUB (Slice 1): the bind/listen/accept logic is not implemented yet —
 * server_listen/server_accept return -1 so the server tests fail. server_close
 * is real (harmless). GREEN fills socket()/bind()/listen()/accept(). */
#include "server.h"

#include <unistd.h>

int server_listen(const char *path) {
    (void)path; /* RED: not implemented — GREEN will socket/bind/listen here. */
    return -1;
}

int server_accept(int listen_fd) {
    (void)listen_fd; /* RED: not implemented — GREEN will accept() here. */
    return -1;
}

void server_close(int fd) {
    if (fd >= 0) {
        close(fd);
    }
}
