/* server — the ECHO packet-shaper's listening UNIX socket (§8 Amendment A1, EP-5). socket/
 * bind/listen/accept, UNIX-domain only — the shaper, like the shim, NEVER opens a network
 * socket (§8.8). Path ownership (chmod/chown) is a separate root seam, deliberately not here,
 * so the hermetic non-root tests bind under a tmp path; bind() leaves the file at the umask. */
#include "server.h"

#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

int shaper_server_listen(const char *path) {
    if (path == NULL) {
        return -1;
    }
    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) {
        return -1;
    }
    int on = 1; /* macOS: suppress SIGPIPE on writes to a closed peer. */
    setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &on, sizeof(on));

    unlink(path); /* remove any stale socket file from a previous run before binding. */

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

int shaper_server_accept(int listen_fd) {
    return accept(listen_fd, NULL, NULL); /* -1 on error */
}

void shaper_server_close(int fd) {
    if (fd >= 0) {
        close(fd);
    }
}
