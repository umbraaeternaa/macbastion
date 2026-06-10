/* VAULT daemon serve loop (§5.6 / §6, VD-1). */
#ifndef VAULT_DAEMON_H
#define VAULT_DAEMON_H

#include "commands.h"

/* Run the IPC serve loop on a connected core fd until EOF or SIGTERM/SIGINT. Returns 0. */
int vault_daemon_run(int fd, vault_runtime_t *rt);

#endif /* VAULT_DAEMON_H */
