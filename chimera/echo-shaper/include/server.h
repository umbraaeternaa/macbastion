/* server — the ECHO packet-shaper's listening UNIX socket (§8 Amendment A1, EP-5). The core
 * connects to us (server side); UNIX-domain only — the shaper, like the shim, NEVER opens a
 * network socket (§8.8). Socket-path ownership (chmod/chown) is a SEPARATE root seam,
 * deliberately NOT here, so the hermetic non-root tests bind under a tmp path. */
#ifndef SHAPER_SERVER_H
#define SHAPER_SERVER_H

/* socket + bind + listen on the UNIX path. Returns the listening fd, or -1 on error. */
int shaper_server_listen(const char *path);

/* Accept one connection on a listening fd. Returns the connected fd, or -1. */
int shaper_server_accept(int listen_fd);

/* Close a socket fd (ignores fd < 0). */
void shaper_server_close(int fd);

#endif /* SHAPER_SERVER_H */
