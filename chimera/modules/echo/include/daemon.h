/* ECHO daemon serve loop (§5.2 / §6). Single-threaded: poll core.sock, dispatch routed
 * echo.* requests, heartbeat. No generation thread (real shaping is gated). */
#ifndef ECHO_DAEMON_H
#define ECHO_DAEMON_H

#include "commands.h"

/* Serve until SIGTERM/SIGINT or the core connection drops. fd must be a connected core
 * socket; rt must be echo_runtime_init'd. Returns an exit code. */
int echo_daemon_run(int fd, echo_runtime_t *rt);

#endif /* ECHO_DAEMON_H */
