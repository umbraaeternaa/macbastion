/* daemon — single-threaded IPC serve loop (§5.8 / §6).
 *
 * poll(500ms) -> read + classify + dispatch routed purge.* commands; heartbeat when due.
 * RESPONSE acks + events are ignored. Exits on EOF (core gone) or SIGTERM/SIGINT. The tier
 * executor is REAL (exec.c: tier0/2/3 destroy); purge.trigger runs it only when ARMED, and an
 * unarmed trigger answers -31004 — so nothing destroys without an explicit operator arm. */
#include "daemon.h"

#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "cJSON.h"

#include "ipc.h"
#include "jsonrpc.h"

#define HEARTBEAT_INTERVAL_S 10
#define IPC_POLL_MS 500

static volatile sig_atomic_t g_stop = 0;

static void on_signal(int sig) {
    (void)sig;
    g_stop = 1;
}

static int send_frame(int fd, const char *json) {
    if (!json) {
        return -1;
    }
    if (ipc_send(fd, json, strlen(json)) != 0) {
        return -1;
    }
    return ipc_send(fd, "\n", 1);
}

static char *build_heartbeat(void) {
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "jsonrpc", "2.0");
    cJSON_AddNumberToObject(root, "id", 0);
    cJSON_AddStringToObject(root, "method", "core.heartbeat");
    cJSON *params = cJSON_CreateObject();
    cJSON_AddStringToObject(params, "module", "purge");
    cJSON_AddItemToObject(root, "params", params);
    char *s = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    return s;
}

static void handle_inbound(int fd, purge_runtime_t *rt, const char *line) {
    if (jsonrpc_classify(line) != JSONRPC_REQUEST) {
        return;
    }
    jsonrpc_request_t *req = NULL;
    if (jsonrpc_parse_request(line, &req) != JSONRPC_OK) {
        return;
    }
    char *resp = purge_commands_dispatch(rt, req->method, req->params, req->id);
    if (resp) {
        send_frame(fd, resp);
        free(resp);
    }
    jsonrpc_request_free(req);
}

int purge_daemon_run(int fd, purge_runtime_t *rt) {
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = on_signal;
    sigaction(SIGTERM, &sa, NULL);
    sigaction(SIGINT, &sa, NULL);

    ipc_reader_t reader;
    ipc_reader_init(&reader, fd);
    char line[16384];
    time_t heartbeat_at = time(NULL);

    while (!g_stop) {
        int pr = ipc_poll(fd, IPC_POLL_MS);
        if (pr < 0) {
            break;
        }
        if (pr == 1) {
            if (ipc_reader_fill(&reader) < 0) {
                break;
            }
            while (ipc_reader_take_line(&reader, line, sizeof(line))) {
                handle_inbound(fd, rt, line);
            }
        }
        time_t now = time(NULL);
        if (now - heartbeat_at >= HEARTBEAT_INTERVAL_S) {
            heartbeat_at = now;
            char *hb = build_heartbeat();
            if (hb) {
                send_frame(fd, hb);
                free(hb);
            }
        }
    }
    return 0;
}
