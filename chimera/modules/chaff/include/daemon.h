/* Daemon coordination: IPC + generation threads, signals (§5.1 Phase B). */
#ifndef CHAFF_DAEMON_H
#define CHAFF_DAEMON_H

#include "commands.h"
#include "endpoints.h"

/* Run until SIGTERM/SIGINT or the core connection drops. Spawns the IPC and
 * generation threads, joins them, returns an exit code. server_fd must be a
 * connected core socket; rt must be chaff_runtime_init'd. */
int daemon_run(int server_fd, chaff_runtime_t *rt, const endpoint_list_t *eps);

#endif /* CHAFF_DAEMON_H */
