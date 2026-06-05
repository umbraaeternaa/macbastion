/* daemon — connect→register→heartbeat→serve scaffold (§5 IPC).
 *
 * STUB (Slice 1): the real socket client + 4A-routed serve loop lands in the
 * daemon-wiring step AFTER the engine is GREEN (mirrors MIRROR's sequence). This
 * slice's tested surface is the pure engine + events + commands. */
#include "daemon.hpp"

namespace tether {

int daemon_run(const DaemonConfig &cfg) {
    (void)cfg; /* STUB: GREEN connects to core and serves tether.* via the router. */
    return 1;
}

} // namespace tether
