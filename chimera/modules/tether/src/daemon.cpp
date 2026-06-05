/* daemon — connect→register→serve loop (§5 IPC).
 *
 * RED STUB (daemon-wiring Slice): daemon_run does NOT register and does NOT serve
 * — it returns immediately, so a spawned binary never registers (integration RED
 * fails on "not registered", like MIRROR's bootstrap). GREEN sends core.register
 * (tether.* methods + only the events it really emits), then runs the inline
 * poll(500ms) loop: serve tether.* via 4A, maybe_tick (source→Monitor.step→emit),
 * maybe_heartbeat (10s). Escalation events are EMIT-ONLY (core enforces, §5). */
#include "daemon.hpp"

namespace tether {

int daemon_run(int core_fd, TetherRuntime &rt, Monitor &mon, RssiSource &src,
               const DaemonConfig &dcfg) {
    (void)core_fd; /* RED: GREEN sends core.register here, then serves. */
    (void)rt;
    (void)mon;
    (void)src;
    (void)dcfg;
    return 1; /* RED: never registers/serves */
}

} // namespace tether
