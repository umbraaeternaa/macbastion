/* TETHER daemon entry (§5.7 §6). Connects OUT to core's command socket, then
 * hands off to daemon_run (which registers + serves). Mirrors MIRROR's main.c,
 * in C++. The daemon serve loop is RED-stubbed this slice; this wiring is real
 * (connect + object setup), so the binary connects but does not yet register. */
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>

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

} // namespace

int main(int argc, char **argv) {
    if (argc > 1 && std::strcmp(argv[1], "--version") == 0) {
        std::printf("TETHER %s\n", tether::VERSION);
        return 0;
    }
    std::signal(SIGPIPE, SIG_IGN);

    /* Defaults; config.json (TETHER_CONFIG_PATH) load lands in GREEN. */
    tether::TetherRuntime rt;
    tether::Monitor mon(rt.presence, rt.escalation, 0.3);
    std::unique_ptr<tether::RssiSource> src = tether::make_source();
    tether::DaemonConfig dcfg;

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
