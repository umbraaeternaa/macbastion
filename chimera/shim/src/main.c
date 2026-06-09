/* CHIMERA privileged-shim daemon entry (§8.8 / §7.10, SHIM.md Slice 1).
 *
 * Wiring only this slice: parse args, open the server socket, accept, check the
 * peer's credentials (LOCAL_PEERCRED), and dispatch one JSON-RPC line per
 * connection. The logic it calls (server/peercred/ops/protocol) is RED-stubbed,
 * so the daemon does nothing useful yet — this file is the honest control-flow
 * skeleton (MANIFESTO §4: no stub that pretends), not a working server.
 *
 * Args:
 *   --socket-path PATH   socket to bind (default /var/run/chimera-shim.sock)
 *   --operator-uid UID   uid the shim trusts as the core (default: getuid())
 *   -m privileged        apply SS-0(b) ownership (root-only; off by default)
 *
 * No secret (Slice 2), no launchd plist (SH-8), no real ops (Slice 3+). */
#include <pwd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "cJSON.h"

#include "jsonrpc.h"
#include "ops.h"
#include "ownership.h"
#include "peercred.h"
#include "protocol.h"
#include "secret.h"
#include "server.h"
#include "shim.h"

#define DEFAULT_SOCKET_PATH "/var/run/chimera-shim.sock"

/* Read one '\n'-terminated line from fd into buf (newline stripped). Returns the
 * length, or -1 on EOF/error/overflow. Minimal inline framing for the skeleton. */
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

/* Serve exactly one request on a connected fd: authenticate the peer, read a
 * line, dispatch, write the response. */
static void serve_one(int conn, uid_t operator_uid, const char *secret) {
    shim_peer_t peer = {0};
    int authorized = 0;
    if (peercred_resolve_current(conn, &peer) == SHIM_OK) {
        authorized = peercred_authorized(&peer, operator_uid);
    }

    char line[16384];
    if (read_line(conn, line, sizeof(line)) < 0) {
        return;
    }

    jsonrpc_request_t *req = NULL;
    if (jsonrpc_parse_request(line, &req) != JSONRPC_OK) {
        return;
    }
    /* 2b-ii will compute this via SecCode peer attestation; fail-closed (0) until then, so
     * shim.handshake issues no secret yet and destructive ops stay sealed. */
    int attested = 0;
    char *resp = protocol_dispatch(req->method, req->params, req->id, authorized, secret, attested);
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
    int privileged = 0;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--socket-path") == 0 && i + 1 < argc) {
            socket_path = argv[++i];
        } else if (strcmp(argv[i], "--operator-uid") == 0 && i + 1 < argc) {
            operator_uid = (uid_t)strtoul(argv[++i], NULL, 10);
        } else if (strcmp(argv[i], "-m") == 0 && i + 1 < argc &&
                   strcmp(argv[i + 1], "privileged") == 0) {
            privileged = 1;
            i++;
        } else {
            fprintf(stderr, "chimera-shim: unknown arg %s\n", argv[i]);
            return 2;
        }
    }

    int listen_fd = server_listen(socket_path);
    if (listen_fd < 0) {
        fprintf(stderr, "chimera-shim: cannot bind %s\n", socket_path);
        return 1;
    }
    if (privileged) {
        /* Reach the socket to the operator's primary group (so the non-root core can
         * connect), not the shim's own root group. */
        gid_t operator_group = getgid();
        const struct passwd *pw = getpwuid(operator_uid);
        if (pw != NULL) {
            operator_group = pw->pw_gid;
        }
        if (ownership_apply(socket_path, operator_group) != SHIM_OK) {
            fprintf(stderr, "chimera-shim: ownership_apply failed (need root)\n");
        }
    }

    /* Per-boot secret (SS-3/SS-4): generated in memory at load, never on disk. */
    char secret[SHIM_SECRET_HEX_LEN + 1];
    secret_generate(secret);

    for (;;) {
        int conn = server_accept(listen_fd);
        if (conn < 0) {
            break;
        }
        serve_one(conn, operator_uid, secret);
        server_close(conn);
    }
    server_close(listen_fd);
    return 0;
}
