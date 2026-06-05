/* Privileged-shim listening socket (SH-2). The shim is a UNIX-domain socket
 * SERVER — core connects to it (the inverse of MIRROR/CHAFF, which are clients
 * to core). socket/bind/listen/accept. UNIX-domain only; the shim NEVER opens
 * a network socket (§8.8).
 *
 * Ownership of the socket path (SS-0(b): chmod 0660 + chown root:operatorgroup)
 * is a SEPARATE root-only seam (ownership.h), not done here — so the hermetic
 * non-root skeleton can bind in a tmp dir without privileges (SS-7). */
#ifndef SHIM_SERVER_H
#define SHIM_SERVER_H

#include "shim.h"

/* Create a listening UNIX-domain stream socket bound at `path`. Removes any
 * stale socket file first. Returns a listen fd >= 0, or -1 on failure. */
int server_listen(const char *path);

/* Block until one client connects; returns the accepted connection fd >= 0,
 * or -1 on error. */
int server_accept(int listen_fd);

void server_close(int fd);

#endif /* SHIM_SERVER_H */
