/* UNIX-socket client to core (§6.3). NDJSON framing, poll-based reads. */
#ifndef MIRROR_IPC_H
#define MIRROR_IPC_H

#include <stddef.h>

#include "mirror.h"

/* Connect to a UNIX socket. Returns a fd >= 0, or -1 on failure. */
int ipc_connect(const char *path);
void ipc_close(int fd);

/* Send exactly len bytes (handles partial writes). Caller frames with '\n'. */
mirror_result_t ipc_send(int fd, const char *data, size_t len);

/* Poll for readability: 1 = readable, 0 = timeout, -1 = error/hangup. */
int ipc_poll(int fd, int timeout_ms);

/* Incremental NDJSON line reader: fill() pulls bytes from the fd (call when
 * poll reports readable); take_line() extracts buffered complete lines. */
typedef struct {
    int fd;
    char buf[16384];
    size_t len;
} ipc_reader_t;

void ipc_reader_init(ipc_reader_t *r, int fd);
/* Read available bytes into the buffer. 0 = ok, -1 = EOF/error/overflow. */
int ipc_reader_fill(ipc_reader_t *r);
/* Pop one complete line (newline stripped) into out. 1 = line, 0 = need more. */
int ipc_reader_take_line(ipc_reader_t *r, char *out, size_t outsz);

#endif /* MIRROR_IPC_H */
