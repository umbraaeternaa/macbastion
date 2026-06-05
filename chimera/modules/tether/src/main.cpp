/* TETHER daemon entry (§5.7). Parses args, builds the daemon config, runs the
 * serve loop. The loop itself is a STUB this slice (daemon-wiring lands after the
 * engine is GREEN); this file is the honest control-flow skeleton. */
#include <cstdio>
#include <cstring>

#include "daemon.hpp"

int main(int argc, char **argv) {
    tether::DaemonConfig cfg{"~/.config/chimera/run", "~/.config/chimera/tether/config.json"};

    for (int i = 1; i < argc; i++) {
        if (std::strcmp(argv[i], "--socket-dir") == 0 && i + 1 < argc) {
            cfg.socket_dir = argv[++i];
        } else if (std::strcmp(argv[i], "--config") == 0 && i + 1 < argc) {
            cfg.config_path = argv[++i];
        } else {
            std::fprintf(stderr, "tether: unknown arg %s\n", argv[i]);
            return 2;
        }
    }
    return tether::daemon_run(cfg);
}
