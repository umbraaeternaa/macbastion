/* Daemon scaffold (§5 IPC, star topology). Connect out to core, register
 * (tether.* methods + events, depends_on per §7), heartbeat, serve tether.* via
 * the 4A router. Like CHAFF/MIRROR, TETHER binds no socket of its own.
 *
 * Slice 1: this is a STUB. The real connect/register/serve loop lands in the
 * daemon-wiring step AFTER the engine is GREEN (mirrors MIRROR's sequence). The
 * unit-tested surface this slice is the pure engine + events + commands. */
#ifndef TETHER_DAEMON_HPP
#define TETHER_DAEMON_HPP

namespace tether {

struct DaemonConfig {
    const char *socket_dir;  /* ~/.config/chimera/run */
    const char *config_path; /* ~/.config/chimera/tether/config.json */
};

/* Run the daemon. Returns a process exit code. STUB this slice. */
int daemon_run(const DaemonConfig &cfg);

} // namespace tether

#endif /* TETHER_DAEMON_HPP */
