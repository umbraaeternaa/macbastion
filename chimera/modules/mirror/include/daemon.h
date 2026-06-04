/* Daemon coordination: a single inline IPC loop + signals (§5.4 §6). MIRROR has
 * no worker thread yet — the CGEventTap (the would-be second thread) is GATED on
 * code-signing + Accessibility TCC, so the daemon is IPC-only for now. */
#ifndef MIRROR_DAEMON_H
#define MIRROR_DAEMON_H

#include "commands.h"

/* Run until SIGTERM/SIGINT or the core connection drops. Runs the IPC loop on
 * the calling thread (no pthread until the tap lands), returns an exit code.
 * server_fd must be a connected core socket; rt must be mirror_runtime_init'd. */
int daemon_run(int server_fd, mirror_runtime_t *rt);

#endif /* MIRROR_DAEMON_H */
