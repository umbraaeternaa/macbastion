/* ipc — UNIX-socket client to core, NDJSON framing, poll-based reads (§6.3). */
#include "ipc.h"

#include <errno.h>
#include <poll.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

int ipc_connect(const char *path) {
    if (!path) {
        return -1;
    }
    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) {
        return -1;
    }
    int on = 1;
    setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &on, sizeof(on));

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, path, sizeof(addr.sun_path) - 1);
    if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(fd);
        return -1;
    }
    return fd;
}

void ipc_close(int fd) {
    if (fd >= 0) {
        close(fd);
    }
}

int ipc_send(int fd, const char *data, size_t len) {
    size_t sent = 0;
    while (sent < len) {
        ssize_t n = write(fd, data + sent, len - sent);
        if (n < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        sent += (size_t)n;
    }
    return 0;
}

int ipc_poll(int fd, int timeout_ms) {
    struct pollfd pfd = {.fd = fd, .events = POLLIN, .revents = 0};
    int rc = poll(&pfd, 1, timeout_ms);
    if (rc < 0) {
        return (errno == EINTR) ? 0 : -1;
    }
    if (rc == 0) {
        return 0;
    }
    if (pfd.revents & (POLLHUP | POLLERR | POLLNVAL)) {
        return -1;
    }
    return (pfd.revents & POLLIN) ? 1 : 0;
}

void ipc_reader_init(ipc_reader_t *r, int fd) {
    r->fd = fd;
    r->len = 0;
}

int ipc_reader_fill(ipc_reader_t *r) {
    if (r->len >= sizeof(r->buf)) {
        return -1; /* buffer full with no newline — overlong frame */
    }
    ssize_t n = read(r->fd, r->buf + r->len, sizeof(r->buf) - r->len);
    if (n <= 0) {
        return -1; /* EOF or error */
    }
    r->len += (size_t)n;
    return 0;
}

int ipc_reader_take_line(ipc_reader_t *r, char *out, size_t outsz) {
    char *nl = memchr(r->buf, '\n', r->len);
    if (!nl) {
        return 0;
    }
    size_t line_len = (size_t)(nl - r->buf);
    size_t copy = (line_len < outsz - 1) ? line_len : outsz - 1;
    memcpy(out, r->buf, copy);
    out[copy] = '\0';
    size_t consumed = line_len + 1;
    memmove(r->buf, r->buf + consumed, r->len - consumed);
    r->len -= consumed;
    return 1;
}
