/* daemon — two threads (IPC + generation) over the shared runtime (§5.1).
 *
 * IPC thread (sole socket writer): poll(500ms) -> read+classify+dispatch routed
 * commands; on each tick drain the event queue and send a heartbeat when due.
 * A poll-based loop (not a blocking read) lets heartbeat + events flow while the
 * generation thread is blocked in a (possibly long) http_get.
 *
 * Generation thread: when GENERATING, pick a category, jitter-sleep, GET, log,
 * and enqueue a chaff.request.sent event for the IPC thread to send.
 */
#include "daemon.h"

#include <stdlib.h>
#include <string.h>

#include "cJSON.h"

#include "chaff.h"
#include "commands.h"
#include "db.h"
#include "generation.h"
#include "http.h"
#include "ipc.h"
#include "jsonrpc.h"

#define HEARTBEAT_INTERVAL_S 10
#define IPC_POLL_MS 500
#define HTTP_TIMEOUT_S 30

typedef struct {
    int fd;
    chaff_runtime_t *rt;
    const endpoint_list_t *eps;
} daemon_ctx_t;

static const char *const CATEGORIES[] = {"news", "tech", "social", "search", "dev"};

/* g_rt lets the (argument-less) signal handler flip the shared stop flag. */
static chaff_runtime_t *g_rt = NULL;

static void on_signal(int sig) {
    (void)sig;
    if (g_rt) {
        g_rt->stop = 1;
    }
}

static void sleep_ms(long ms) {
    struct timespec ts = {ms / 1000, (ms % 1000) * 1000000L};
    nanosleep(&ts, NULL); /* interrupted by a signal -> returns early (good) */
}

/* Send one NDJSON frame (JSON + newline terminator). */
static chaff_result_t send_frame(int fd, const char *json) {
    if (!json) {
        return CHAFF_ERR;
    }
    chaff_result_t r = ipc_send(fd, json, strlen(json));
    if (r == CHAFF_OK) {
        r = ipc_send(fd, "\n", 1);
    }
    return r;
}

/* Append an event to the queue. Caller must hold rt->mutex. Takes ownership of line. */
static void evq_push(chaff_runtime_t *rt, char *line) {
    chaff_event_t *e = malloc(sizeof(*e));
    if (!e) {
        free(line);
        return;
    }
    e->line = line;
    e->next = NULL;
    if (rt->evq_tail) {
        rt->evq_tail->next = e;
    } else {
        rt->evq_head = e;
    }
    rt->evq_tail = e;
}

static char *build_heartbeat(void) {
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "jsonrpc", "2.0");
    cJSON_AddNumberToObject(root, "id", 0); /* request id; the ack is ignored */
    cJSON_AddStringToObject(root, "method", "core.heartbeat");
    cJSON *params = cJSON_CreateObject();
    cJSON_AddStringToObject(params, "module", "chaff");
    cJSON_AddItemToObject(root, "params", params);
    char *s = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    return s;
}

static char *build_request_sent(const char *url, long gap_ms, chaff_result_t r) {
    cJSON *p = cJSON_CreateObject();
    cJSON_AddStringToObject(p, "endpoint", url);
    cJSON_AddNumberToObject(p, "gap_ms", (double)gap_ms);
    cJSON_AddBoolToObject(p, "ok", r == CHAFF_OK);
    return jsonrpc_serialize_notification("chaff.request.sent", p);
}

/* Dispatch one inbound frame: only routed REQUESTs are served; acks/events ignored. */
static void handle_inbound(daemon_ctx_t *ctx, const char *line) {
    if (jsonrpc_classify(line) != JSONRPC_REQUEST) {
        return;
    }
    jsonrpc_request_t *req = NULL;
    if (jsonrpc_parse_request(line, &req) != CHAFF_OK) {
        return;
    }
    pthread_mutex_lock(&ctx->rt->mutex);
    char *resp = commands_dispatch(ctx->rt, ctx->eps, req->method, req->params, req->id);
    pthread_mutex_unlock(&ctx->rt->mutex);
    if (resp) {
        send_frame(ctx->fd, resp);
        free(resp);
    }
    jsonrpc_request_free(req);
}

static void drain_events(daemon_ctx_t *ctx) {
    for (;;) {
        pthread_mutex_lock(&ctx->rt->mutex);
        chaff_event_t *e = ctx->rt->evq_head;
        if (e) {
            ctx->rt->evq_head = e->next;
            if (!ctx->rt->evq_head) {
                ctx->rt->evq_tail = NULL;
            }
        }
        pthread_mutex_unlock(&ctx->rt->mutex);
        if (!e) {
            break;
        }
        send_frame(ctx->fd, e->line);
        free(e->line);
        free(e);
    }
}

static void maybe_heartbeat(daemon_ctx_t *ctx) {
    time_t now = time(NULL);
    pthread_mutex_lock(&ctx->rt->mutex);
    int due = (now - ctx->rt->heartbeat_at) >= HEARTBEAT_INTERVAL_S;
    if (due) {
        ctx->rt->heartbeat_at = now;
    }
    pthread_mutex_unlock(&ctx->rt->mutex);
    if (due) {
        char *hb = build_heartbeat();
        if (hb) {
            send_frame(ctx->fd, hb);
            free(hb);
        }
    }
}

static void *ipc_thread(void *arg) {
    daemon_ctx_t *ctx = arg;
    ipc_reader_t reader;
    ipc_reader_init(&reader, ctx->fd);
    char line[16384];
    while (!ctx->rt->stop) {
        int pr = ipc_poll(ctx->fd, IPC_POLL_MS);
        if (pr < 0) {
            ctx->rt->stop = 1; /* core dropped -> exit (no supervisor yet) */
            break;
        }
        if (pr == 1) {
            if (ipc_reader_fill(&reader) < 0) {
                ctx->rt->stop = 1;
                break;
            }
            while (ipc_reader_take_line(&reader, line, sizeof(line))) {
                handle_inbound(ctx, line);
            }
        }
        drain_events(ctx);
        maybe_heartbeat(ctx);
    }
    return NULL;
}

static void *gen_thread(void *arg) {
    daemon_ctx_t *ctx = arg;
    pthread_mutex_lock(&ctx->rt->mutex);
    uint64_t rng = ctx->rt->rng_state; /* private copy; only this thread uses it */
    pthread_mutex_unlock(&ctx->rt->mutex);

    while (!ctx->rt->stop) {
        pthread_mutex_lock(&ctx->rt->mutex);
        chaff_state_t state = ctx->rt->state;
        double gap = ctx->rt->base_gap_ms;
        pthread_mutex_unlock(&ctx->rt->mutex);

        if (state != CHAFF_GENERATING) {
            sleep_ms(IPC_POLL_MS);
            continue;
        }
        const char *cat = CATEGORIES[chaff_rng_next(&rng) % 5];
        gen_plan_t plan;
        if (generation_plan_next(ctx->eps, cat, gap, &rng, &plan) != CHAFF_OK) {
            sleep_ms(IPC_POLL_MS);
            continue;
        }
        sleep_ms(plan.jitter_ms);
        if (ctx->rt->stop) {
            break;
        }
        chaff_result_t r = http_get(plan.endpoint->url, HTTP_TIMEOUT_S);
        char *ev = build_request_sent(plan.endpoint->url, plan.jitter_ms, r);
        pthread_mutex_lock(&ctx->rt->mutex);
        ctx->rt->requests_today++;
        if (ctx->rt->db) {
            db_insert_generation(ctx->rt->db, plan.endpoint->url, (int64_t)time(NULL),
                                 r == CHAFF_OK ? 200 : 0);
        }
        if (ev) {
            evq_push(ctx->rt, ev);
        }
        pthread_mutex_unlock(&ctx->rt->mutex);
    }
    return NULL;
}

int daemon_run(int server_fd, chaff_runtime_t *rt, const endpoint_list_t *eps) {
    g_rt = rt;
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = on_signal;
    sigaction(SIGTERM, &sa, NULL);
    sigaction(SIGINT, &sa, NULL);

    daemon_ctx_t ctx = {.fd = server_fd, .rt = rt, .eps = eps};
    pthread_t ipc_tid, gen_tid;
    pthread_create(&ipc_tid, NULL, ipc_thread, &ctx);
    pthread_create(&gen_tid, NULL, gen_thread, &ctx);
    pthread_join(ipc_tid, NULL);
    pthread_join(gen_tid, NULL);
    return 0;
}
