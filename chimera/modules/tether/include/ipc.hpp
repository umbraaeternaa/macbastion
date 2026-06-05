/* ipc — UNIX-socket client to core (§6.3), NDJSON framing, poll-based reads.
 * Fresh C++ (NOT a copy) — TETHER connects OUT to core like CHAFF/MIRROR but the
 * socket helpers are written here in C++ rather than copying mirror's ipc.c
 * (only jsonrpc.c is the deliberate 4th copy, TE-7b). */
#ifndef TETHER_IPC_HPP
#define TETHER_IPC_HPP

#include <cstddef>

namespace tether {

/* Connect to a UNIX socket; returns fd >= 0, or -1 on failure. */
int ipc_connect(const char *path);
void ipc_close(int fd);

/* Send exactly len bytes (handles partial writes). Caller frames with '\n'. */
bool ipc_send(int fd, const char *data, std::size_t len);

/* Poll for readability: 1 = readable, 0 = timeout, -1 = error/hangup. */
int ipc_poll(int fd, int timeout_ms);

/* Incremental NDJSON line reader. */
class IpcReader {
  public:
    explicit IpcReader(int fd) : fd_(fd), len_(0) {}
    /* Pull available bytes; 0 = ok, -1 = EOF/error/overflow. */
    int fill();
    /* Pop one complete line (newline stripped); 1 = line, 0 = need more. */
    int take_line(char *out, std::size_t outsz);

  private:
    int fd_;
    char buf_[16384];
    std::size_t len_;
};

} // namespace tether

#endif /* TETHER_IPC_HPP */
