/* daemon — single inline IPC loop over the shared runtime (§5.4 §6).
 *
 * One thread (the caller's): poll(500ms) -> read+classify+dispatch routed
 * commands; on each tick drain the event queue and send a heartbeat when due.
 * Unlike CHAFF there is no second worker thread — MIRROR's worker would be the
 * CGEventTap, which is GATED on code-signing + Accessibility TCC. So there is
 * also no event PRODUCER yet: drain_events is wired forward-compat (it will ship
 * tap-sourced events once the tap lands) but the queue stays empty for now.
 */
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

/* g_rt lets the (argument-less) signal handler flip the shared stop flag. */
static mirror_runtime_t *g_rt = NULL;

static void on_signal(int sig) {
    (void)sig;
    if (g_rt) {
        g_rt->stop = 1;
    }
}

/* Send one NDJSON frame (JSON + newline terminator). */
static mirror_result_t send_frame(int fd, const char *json) {
    if (!json) {
        return MIRROR_ERR;
    }
    mirror_result_t r = ipc_send(fd, json, strlen(json));
    if (r == MIRROR_OK) {
        r = ipc_send(fd, "\n", 1);
    }
    return r;
}

static char *build_heartbeat(void) {
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "jsonrpc", "2.0");
    cJSON_AddNumberToObject(root, "id", 0); /* request id; the ack is ignored */
    cJSON_AddStringToObject(root, "method", "core.heartbeat");
    cJSON *params = cJSON_CreateObject();
    cJSON_AddStringToObject(params, "module", "mirror");
    cJSON_AddItemToObject(root, "params", params);
    char *s = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    return s;
}

/* Dispatch one inbound frame: only routed REQUESTs are served; acks/events ignored. */
static void handle_inbound(int fd, mirror_runtime_t *rt, const char *line) {
    if (jsonrpc_classify(line) != JSONRPC_REQUEST) {
        return;
    }
    jsonrpc_request_t *req = NULL;
    if (jsonrpc_parse_request(line, &req) != MIRROR_OK) {
        return;
    }
    pthread_mutex_lock(&rt->mutex);
    char *resp = commands_dispatch(rt, req->method, req->params, req->id);
    pthread_mutex_unlock(&rt->mutex);
    if (resp) {
        send_frame(fd, resp);
        free(resp);
    }
    jsonrpc_request_free(req);
}

/* Forward-compat: ships any queued events. No producer yet (the tap is gated),
 * so the queue is empty today — this is the seam the tap will plug into. */
static void drain_events(int fd, mirror_runtime_t *rt) {
    for (;;) {
        pthread_mutex_lock(&rt->mutex);
        mirror_event_node_t *e = rt->evq_head;
        if (e) {
            rt->evq_head = e->next;
            if (!rt->evq_head) {
                rt->evq_tail = NULL;
            }
        }
        pthread_mutex_unlock(&rt->mutex);
        if (!e) {
            break;
        }
        send_frame(fd, e->line);
        free(e->line);
        free(e);
    }
}

static void maybe_heartbeat(int fd, mirror_runtime_t *rt) {
    time_t now = time(NULL);
    pthread_mutex_lock(&rt->mutex);
    int due = (now - rt->heartbeat_at) >= HEARTBEAT_INTERVAL_S;
    if (due) {
        rt->heartbeat_at = now;
    }
    pthread_mutex_unlock(&rt->mutex);
    if (due) {
        char *hb = build_heartbeat();
        if (hb) {
            send_frame(fd, hb);
            free(hb);
        }
    }
}

int daemon_run(int server_fd, mirror_runtime_t *rt) {
    g_rt = rt;
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = on_signal;
    sigaction(SIGTERM, &sa, NULL);
    sigaction(SIGINT, &sa, NULL);

    ipc_reader_t reader;
    ipc_reader_init(&reader, server_fd);
    char line[16384];
    while (!rt->stop) {
        int pr = ipc_poll(server_fd, IPC_POLL_MS);
        if (pr < 0) {
            rt->stop = 1; /* core dropped -> exit (no supervisor yet) */
            break;
        }
        if (pr == 1) {
            if (ipc_reader_fill(&reader) < 0) {
                rt->stop = 1;
                break;
            }
            while (ipc_reader_take_line(&reader, line, sizeof(line))) {
                handle_inbound(server_fd, rt, line);
            }
        }
        drain_events(server_fd, rt);
        maybe_heartbeat(server_fd, rt);
    }
    return 0;
}
