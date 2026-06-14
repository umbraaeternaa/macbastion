/* CHIMERA ECHO packet-shaper daemon entry (§8 Amendment A1, EP-5, docs/ECHO_PACKET.md).
 *
 * Wiring (mirrors the shim's serve-one-request loop): parse args, open the UNIX server
 * socket, accept, authenticate the peer (LOCAL_PEERCRED), and dispatch one JSON-RPC line
 * per connection against the per-boot secret. The pf/dnctl effects behind the dispatch are
 * still FAIL-OPEN no-ops (shaper_execute / anchor seam) — the real pf path lands in a later
 * gated slice on a throwaway anchor, with per-command root approval (§4: no stub that
 * pretends). ROOT-FREE: opens only a UNIX-domain socket (§8.8), never a network socket, and
 * runs no privileged op. No socket-path ownership here — that chmod/chown is a SEPARATE root
 * seam (server.h), deliberately out of this root-free skeleton. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "jsonrpc.h"
#include "peercred.h"
#include "protocol.h"
#include "secret.h"
#include "server.h"

#define DEFAULT_SOCKET_PATH "/var/run/chimera-echo-shaper.sock"

/* Read one '\n'-terminated line from fd into buf (newline stripped). Returns the length, or
 * -1 on EOF/error/overflow. Minimal inline framing, mirrors the shim. */
static long read_line(int fd, char *buf, size_t cap) {
    size_t len = 0;
    while (len + 1 < cap) {
        char c;
        ssize_t n = read(fd, &c, 1);
        if (n <= 0) {
            return -1;
        }
        if (c == '\n') {
            buf[len] = '\0';
            return (long)len;
        }
        buf[len++] = c;
    }
    return -1; /* overlong frame */
}

/* Serve exactly one request on a connected fd: authenticate the peer (LOCAL_PEERCRED), read a
 * line, dispatch against the per-boot secret, write the response. */
static void serve_one(int conn, uid_t operator_uid, const char *secret) {
    shaper_peer_t peer = {0};
    int authorized = 0;
    if (shaper_peercred_resolve_current(conn, &peer) == SHAPER_OK) {
        authorized = shaper_peercred_authorized(&peer, operator_uid);
    }

    char line[16384];
    if (read_line(conn, line, sizeof(line)) < 0) {
        return;
    }

    jsonrpc_request_t *req = NULL;
    if (jsonrpc_parse_request(line, &req) != JSONRPC_OK) {
        return;
    }
    char *resp = shaper_protocol_dispatch(req->method, req->params, req->id, authorized, secret);
    if (resp) {
        (void)write(conn, resp, strlen(resp));
        (void)write(conn, "\n", 1);
        free(resp);
    }
    jsonrpc_request_free(req);
}

int main(int argc, char **argv) {
    const char *socket_path = DEFAULT_SOCKET_PATH;
    uid_t operator_uid = getuid();

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--socket-path") == 0 && i + 1 < argc) {
            socket_path = argv[++i];
        } else if (strcmp(argv[i], "--operator-uid") == 0 && i + 1 < argc) {
            operator_uid = (uid_t)strtoul(argv[++i], NULL, 10);
        } else {
            fprintf(stderr, "chimera-echo-shaper: unknown arg %s\n", argv[i]);
            return 2;
        }
    }

    int listen_fd = shaper_server_listen(socket_path);
    if (listen_fd < 0) {
        fprintf(stderr, "chimera-echo-shaper: cannot bind %s\n", socket_path);
        return 1;
    }

    /* Per-boot secret (EP-5): generated in memory at load, never on disk. */
    char secret[SHAPER_SECRET_HEX_LEN + 1];
    shaper_secret_generate(secret);

    for (;;) {
        int conn = shaper_server_accept(listen_fd);
        if (conn < 0) {
            break;
        }
        serve_one(conn, operator_uid, secret);
        shaper_server_close(conn);
    }
    shaper_server_close(listen_fd);
    return 0;
}
