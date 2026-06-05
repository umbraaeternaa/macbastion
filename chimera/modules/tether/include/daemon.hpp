/* Daemon coordination — connect→register→serve, mirroring MIRROR's single inline
 * IPC loop (§5 IPC, star topology). One core.sock connection: register, serve
 * tether.* via the 4A router, emit events as notifications, heartbeat. Plus a
 * TICK cadence (TETHER's producer, which MIRROR lacked): each tick pulls a sample
 * from the source, runs Monitor.step, and emits the resulting events.
 *
 * EMIT-ONLY (spec §5): escalation events are REQUESTS — core enforces L1/L2/L3.
 * The source is gated in production (CoreBluetoothSource yields nothing), so the
 * daemon ticks but emits no presence until the .mm lands. */
#ifndef TETHER_DAEMON_HPP
#define TETHER_DAEMON_HPP

#include "commands.hpp"
#include "monitor.hpp"
#include "source.hpp"

namespace tether {

struct DaemonConfig {
    long tick_ms = 2000;       /* §3 default TICK */
    long heartbeat_ms = 10000; /* §7.11 default; TETHER-specific shorter-liveness is an open Q */
};

/* core_fd is an already-connected core socket (main connects). daemon_run sends
 * core.register, then runs the poll/tick/heartbeat/serve loop until SIGTERM/
 * SIGINT or core drop. Returns a process exit code. */
int daemon_run(int core_fd, TetherRuntime &rt, Monitor &mon, RssiSource &src,
               const DaemonConfig &dcfg);

} // namespace tether

#endif /* TETHER_DAEMON_HPP */
