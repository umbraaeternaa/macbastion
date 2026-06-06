/* daemon — connect→register→serve loop (§5 IPC), mirroring MIRROR's single inline
 * loop, plus TETHER's producer: a TICK cadence that pulls a sample, runs
 * Monitor.step, and emits the resulting events as JSON-RPC notifications.
 *
 * EMIT-ONLY (spec §5): escalation events are REQUESTS — core enforces L1/L2/L3.
 * The daemon never locks/evicts/reboots. The source is gated in production
 * (CoreBluetoothSource yields nothing), so the daemon ticks but emits no presence
 * until the .mm lands — it never fabricates presence (§4). */
#include "daemon.hpp"

#include <csignal>
#include <cstdlib>
#include <cstring>

#include "cJSON.h"

#include "clock.hpp"
#include "events.hpp"
#include "ipc.hpp"
#include "jsonrpc.h"
#include "tether.hpp"

namespace tether {

namespace {

volatile sig_atomic_t g_stop = 0;
void on_signal(int sig) {
    (void)sig;
    g_stop = 1;
}

bool send_frame(int fd, const char *json) {
    if (!json) {
        return false;
    }
    bool ok = ipc_send(fd, json, std::strlen(json));
    if (ok) {
        ok = ipc_send(fd, "\n", 1);
    }
    return ok;
}

char *build_register() {
    static const char *const METHODS[] = {
        "tether.status",   "tether.config.set",       "tether.l3.arm",
        "tether.l3.disarm", "tether.escalation.cancel", "tether.test",
        "tether.heighten", "tether.relax",
        "tether.pair.start", "tether.pair.confirm",     "tether.unpair",
    };
    /* Only events the daemon actually emits this slice (Monitor transitions). */
    static const char *const EVENTS[] = {
        "tether.present",   "tether.fringe",    "tether.absent",
        "tether.escalation", "tether.recovered", "tether.suspicious",
    };
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "jsonrpc", "2.0");
    cJSON_AddNumberToObject(root, "id", 1);
    cJSON_AddStringToObject(root, "method", "core.register");
    cJSON *p = cJSON_CreateObject();
    cJSON_AddStringToObject(p, "module", "tether");
    cJSON_AddStringToObject(p, "version", VERSION);
    cJSON *methods = cJSON_CreateArray();
    for (const char *m : METHODS) {
        cJSON_AddItemToArray(methods, cJSON_CreateString(m));
    }
    cJSON_AddItemToObject(p, "methods", methods);
    cJSON *events = cJSON_CreateArray();
    for (const char *e : EVENTS) {
        cJSON_AddItemToArray(events, cJSON_CreateString(e));
    }
    cJSON_AddItemToObject(p, "events", events);
    /* depends_on=[]: TETHER emits; core relays to VAULT/PURGE when they exist.
     * It does not require them to function (escalation is core-enforced). */
    cJSON_AddItemToObject(p, "depends_on", cJSON_CreateArray());
    cJSON_AddItemToObject(root, "params", p);
    char *s = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    return s;
}

char *build_heartbeat() {
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "jsonrpc", "2.0");
    cJSON_AddNumberToObject(root, "id", 0);
    cJSON_AddStringToObject(root, "method", "core.heartbeat");
    cJSON *p = cJSON_CreateObject();
    cJSON_AddStringToObject(p, "module", "tether");
    cJSON_AddItemToObject(root, "params", p);
    char *s = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    return s;
}

const char *action_for(Stage s) {
    switch (s) {
    case Stage::L1:
        return "lock_screen";
    case Stage::L2:
        return "lock_vaults";
    case Stage::L3:
        return "trigger_purge";
    case Stage::NONE:
        return "";
    }
    return "";
}

/* Map a MonitorEvent to a (method, params) notification and send it. EMIT-ONLY. */
void emit_event(int fd, const MonitorEvent &e, long now_ms) {
    const char *method = nullptr;
    cJSON *params = nullptr;
    switch (e.kind) {
    case EventKind::PRESENT:
        method = "tether.present";
        params = event_present(e.rssi_smoothed);
        break;
    case EventKind::FRINGE:
        method = "tether.fringe";
        params = event_fringe(e.rssi_smoothed, e.ticks_missed);
        break;
    case EventKind::ABSENT:
        method = "tether.absent";
        params = event_absent(now_ms, e.rssi_smoothed, e.how);
        break;
    case EventKind::ESCALATION:
        method = "tether.escalation";
        params = event_escalation(e.stage, action_for(e.stage), e.grace_remaining_ms);
        break;
    case EventKind::RECOVERED:
        method = "tether.recovered";
        params = event_recovered(e.stage, e.rssi_smoothed);
        break;
    case EventKind::SUSPICIOUS:
        method = "tether.suspicious";
        params = event_suspicious("instant_drop", e.delayed_by_sec);
        break;
    }
    char *frame = jsonrpc_serialize_notification(method, params);
    if (frame) {
        send_frame(fd, frame);
        std::free(frame);
    }
}

void handle_inbound(int fd, TetherRuntime &rt, Monitor &mon, const char *line) {
    if (jsonrpc_classify(line) != JSONRPC_REQUEST) {
        return;
    }
    jsonrpc_request_t *req = nullptr;
    if (jsonrpc_parse_request(line, &req) != TETHER_OK) {
        return;
    }
    char *resp = commands_dispatch(&rt, req->method, req->params, req->id);
    /* Keep the Monitor in sync with the runtime: L3 gate (l3.arm/disarm) and the
     * heightened flag (heighten/relax) — the live ladder re-arms accordingly. */
    mon.set_l3_armed(rt.escalation.l3_armed);
    mon.set_heightened(rt.heightened);
    if (resp) {
        send_frame(fd, resp);
        std::free(resp);
    }
    jsonrpc_request_free(req);
}

} // namespace

int daemon_run(int core_fd, TetherRuntime &rt, Monitor &mon, RssiSource &src,
               const DaemonConfig &dcfg) {
    struct sigaction sa;
    std::memset(&sa, 0, sizeof(sa));
    sa.sa_handler = on_signal;
    sigaction(SIGTERM, &sa, nullptr);
    sigaction(SIGINT, &sa, nullptr);

    char *reg = build_register();
    if (reg) {
        send_frame(core_fd, reg);
        std::free(reg);
    }

    SystemClock clock;
    long last_tick = clock.now_ms();
    long last_hb = last_tick;
    const int poll_ms = (dcfg.tick_ms < 500) ? static_cast<int>(dcfg.tick_ms) : 500;

    IpcReader reader(core_fd);
    char line[16384];
    while (!g_stop) {
        int pr = ipc_poll(core_fd, poll_ms);
        if (pr < 0) {
            break; /* core dropped -> exit (no supervisor yet) */
        }
        if (pr == 1) {
            if (reader.fill() < 0) {
                break;
            }
            while (reader.take_line(line, sizeof(line))) {
                handle_inbound(core_fd, rt, mon, line);
            }
        }

        long now = clock.now_ms();
        if (now - last_tick >= dcfg.tick_ms) {
            last_tick = now;
            Sample sample{};
            if (src.next(sample)) {
                std::vector<MonitorEvent> events = mon.step(sample, now);
                for (const MonitorEvent &e : events) {
                    emit_event(core_fd, e, now);
                }
                rt.state = mon.state();
                rt.rssi_smoothed = mon.rssi_smoothed();
                rt.escalation_stage = mon.stage();
            }
        }
        if (now - last_hb >= dcfg.heartbeat_ms) {
            last_hb = now;
            char *hb = build_heartbeat();
            if (hb) {
                send_frame(core_fd, hb);
                std::free(hb);
            }
        }
    }
    return 0;
}

} // namespace tether
