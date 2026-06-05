/* TETHER daemon entry (§5.7 §6). Loads config (TETHER_CONFIG_PATH, non-fatal),
 * connects OUT to core's command socket, then hands off to daemon_run (which
 * registers + serves). Mirrors MIRROR's main.c, in C++. */
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <memory>
#include <sstream>
#include <string>

#include "cJSON.h"

#include "commands.hpp"
#include "daemon.hpp"
#include "ipc.hpp"
#include "monitor.hpp"
#include "source.hpp"
#include "tether.hpp"

namespace {

void core_socket_path(char *out, std::size_t outsz) {
    const char *dir = std::getenv("CHIMERA_SOCKET_DIR");
    if (dir) {
        std::snprintf(out, outsz, "%s/core.sock", dir);
    } else {
        const char *home = std::getenv("HOME");
        std::snprintf(out, outsz, "%s/.config/chimera/run/core.sock", home ? home : ".");
    }
}

/* Apply config.json over runtime + daemon defaults (non-fatal — a missing or
 * malformed file leaves defaults intact, like MIRROR). */
void apply_config(tether::TetherRuntime &rt, tether::DaemonConfig &dcfg, const char *path) {
    if (!path) {
        return;
    }
    std::ifstream in(path);
    if (!in) {
        return;
    }
    std::stringstream ss;
    ss << in.rdbuf();
    cJSON *root = cJSON_Parse(ss.str().c_str());
    if (!root) {
        return;
    }
    cJSON *tick = cJSON_GetObjectItemCaseSensitive(root, "tick_ms");
    if (cJSON_IsNumber(tick)) {
        dcfg.tick_ms = static_cast<long>(tick->valuedouble);
    }
    cJSON *nt = cJSON_GetObjectItemCaseSensitive(root, "near_threshold");
    if (cJSON_IsNumber(nt)) {
        rt.presence.near_threshold = nt->valuedouble;
    }
    cJSON *grace = cJSON_GetObjectItemCaseSensitive(root, "grace_ms");
    if (cJSON_IsNumber(grace)) {
        rt.escalation.grace_ms = static_cast<long>(grace->valuedouble);
    }
    cJSON_Delete(root);
}

} // namespace

int main(int argc, char **argv) {
    if (argc > 1 && std::strcmp(argv[1], "--version") == 0) {
        std::printf("TETHER %s\n", tether::VERSION);
        return 0;
    }
    std::signal(SIGPIPE, SIG_IGN);

    tether::TetherRuntime rt;
    tether::DaemonConfig dcfg;
    apply_config(rt, dcfg, std::getenv("TETHER_CONFIG_PATH"));

    /* Monitor is built from the (config-applied) runtime config. */
    tether::Monitor mon(rt.presence, rt.escalation, 0.3);
    std::unique_ptr<tether::RssiSource> src = tether::make_source();

    char sock[1024];
    core_socket_path(sock, sizeof(sock));
    int fd = tether::ipc_connect(sock);
    if (fd < 0) {
        std::fprintf(stderr, "tether: cannot connect to %s\n", sock);
        return 1;
    }

    int rc = tether::daemon_run(fd, rt, mon, *src, dcfg);
    tether::ipc_close(fd);
    return rc;
}
