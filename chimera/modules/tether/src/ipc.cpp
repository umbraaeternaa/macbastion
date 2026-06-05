/* ipc — UNIX-socket client to core, NDJSON framing, poll-based reads (§6.3).
 * Real plumbing (the daemon's transport); not unit-tested directly — exercised
 * by the integration suite against a live core. */
#include "ipc.hpp"

#include <cerrno>
#include <cstring>
#include <poll.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

namespace tether {

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
    std::memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    std::strncpy(addr.sun_path, path, sizeof(addr.sun_path) - 1);
    if (connect(fd, reinterpret_cast<struct sockaddr *>(&addr), sizeof(addr)) < 0) {
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

bool ipc_send(int fd, const char *data, std::size_t len) {
    std::size_t sent = 0;
    while (sent < len) {
        ssize_t n = write(fd, data + sent, len - sent);
        if (n < 0) {
            if (errno == EINTR) {
                continue;
            }
            return false;
        }
        sent += static_cast<std::size_t>(n);
    }
    return true;
}

int ipc_poll(int fd, int timeout_ms) {
    struct pollfd pfd = {fd, POLLIN, 0};
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

int IpcReader::fill() {
    if (len_ >= sizeof(buf_)) {
        return -1; /* overlong frame */
    }
    ssize_t n = read(fd_, buf_ + len_, sizeof(buf_) - len_);
    if (n <= 0) {
        return -1; /* EOF or error */
    }
    len_ += static_cast<std::size_t>(n);
    return 0;
}

int IpcReader::take_line(char *out, std::size_t outsz) {
    char *nl = static_cast<char *>(std::memchr(buf_, '\n', len_));
    if (!nl) {
        return 0;
    }
    std::size_t line_len = static_cast<std::size_t>(nl - buf_);
    std::size_t copy = (line_len < outsz - 1) ? line_len : outsz - 1;
    std::memcpy(out, buf_, copy);
    out[copy] = '\0';
    std::size_t consumed = line_len + 1;
    std::memmove(buf_, buf_ + consumed, len_ - consumed);
    len_ -= consumed;
    return 1;
}

} // namespace tether
