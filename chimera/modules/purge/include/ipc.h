/* UNIX-socket client to core (§6.3). NDJSON framing, poll-based reads. Mirrors CHAFF/ECHO,
 * returns plain int (0 ok / -1 error). */
#ifndef PURGE_IPC_H
#define PURGE_IPC_H

#include <stddef.h>

int ipc_connect(const char *path);
void ipc_close(int fd);
int ipc_send(int fd, const char *data, size_t len);
int ipc_poll(int fd, int timeout_ms);

typedef struct {
    int fd;
    char buf[16384];
    size_t len;
} ipc_reader_t;

void ipc_reader_init(ipc_reader_t *r, int fd);
int ipc_reader_fill(ipc_reader_t *r);
int ipc_reader_take_line(ipc_reader_t *r, char *out, size_t outsz);

#endif /* PURGE_IPC_H */
