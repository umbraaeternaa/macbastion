/* PURGE daemon serve loop (§5.8 / §6). Single-threaded: poll core.sock, dispatch routed
 * purge.* requests, heartbeat. purge.trigger stays gated (no destruction engine). */
#ifndef PURGE_DAEMON_H
#define PURGE_DAEMON_H

#include "commands.h"

/* Serve until SIGTERM/SIGINT or the core connection drops. fd must be a connected core
 * socket; rt must be purge_runtime_init'd. Returns an exit code. */
int purge_daemon_run(int fd, purge_runtime_t *rt);

#endif /* PURGE_DAEMON_H */
