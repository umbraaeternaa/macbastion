/* server — privileged-shim listening UNIX socket (SH-2). SERVER side: core
 * connects to us (inverse of MIRROR/CHAFF clients). socket/bind/listen/accept,
 * UNIX-domain only — the shim NEVER opens a network socket (§8.8).
 *
 * Socket-path ownership (SS-0(b): chmod 0660 + chown root:operatorgroup) is a
 * SEPARATE root-only seam (ownership.c), deliberately NOT applied here, so the
 * hermetic non-root skeleton can bind under a tmp path without privileges (SS-7).
 * Here bind() just leaves the file at the process umask default. */
#include "server.h"

#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

int server_listen(const char *path) {
    if (!path) {
        return -1;
    }
    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) {
        return -1;
    }
    /* macOS: suppress SIGPIPE on writes to a closed peer. */
    int on = 1;
    setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &on, sizeof(on));

    /* Remove any stale socket file from a previous run before binding. */
    unlink(path);

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, path, sizeof(addr.sun_path) - 1);
    if (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(fd);
        return -1;
    }
    if (listen(fd, 4) < 0) {
        close(fd);
        return -1;
    }
    return fd;
}

int server_accept(int listen_fd) {
    return accept(listen_fd, NULL, NULL); /* -1 on error */
}

void server_close(int fd) {
    if (fd >= 0) {
        close(fd);
    }
}
