/* tcc-disclaim — launch a child with its TCC responsibility DISCLAIMED, so the child
 * becomes its OWN TCC subject (its own code signature + embedded Info.plist usage
 * strings) instead of being attributed to this launcher or its parent.
 *
 * Why CHIMERA needs it: native daemons (e.g. TETHER) are spawned by the Python
 * supervisor. macOS attributes their TCC requests to the RESPONSIBLE process — which
 * resolves up the launchd graph to the supervisor's python, an interpreter with no
 * Bluetooth usage description. So TETHER's CBCentralManager request is silently
 * DENIED and no prompt is ever shown. Spawning the daemon through this launcher with
 * responsibility_spawnattrs_setdisclaim() makes the daemon responsible for itself, so
 * it raises its OWN "tether would like to use Bluetooth" prompt and matches a grant
 * keyed to com.umbra.chimera.tether. The grant then survives rebuilds (stable signing
 * identity) — that is the whole point.
 *
 * It is a FAITHFUL PROXY of one child: forwards SIGTERM/SIGINT and exits with the
 * child's status, so a supervisor that tracks THIS pid still fully controls the
 * child. (No-op transparent passthrough for everything else.) */
#include <signal.h>
#include <spawn.h>
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>

/* Private libSystem API (used by sandbox-exec and friends): make the spawned process
 * disclaim its parent's TCC responsibility and become responsible for itself. Declared
 * here because the header (<spawn_private.h>) is not in the public SDK; the symbol is
 * exported by libSystem and links normally. */
extern int responsibility_spawnattrs_setdisclaim(posix_spawnattr_t *attrs, int disclaim);

extern char **environ;

static pid_t g_child = 0;

/* Forward the terminating signal to the child so the supervisor's SIGTERM reaches the
 * real daemon (we are only a thin shell around it). */
static void forward_signal(int sig) {
    if (g_child > 0) {
        kill(g_child, sig);
    }
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: tcc-disclaim <program> [args...]\n");
        return 2;
    }

    posix_spawnattr_t attrs;
    if (posix_spawnattr_init(&attrs) != 0) {
        fprintf(stderr, "tcc-disclaim: posix_spawnattr_init failed\n");
        return 126;
    }
    /* THE point of this launcher: the child disclaims our responsibility and becomes
     * its own TCC subject. */
    responsibility_spawnattrs_setdisclaim(&attrs, 1);

    /* Install forwarders before spawning so an early SIGTERM is not lost (the tiny
     * window before g_child is set is harmless — default disposition would just exit). */
    signal(SIGTERM, forward_signal);
    signal(SIGINT, forward_signal);

    pid_t pid = 0;
    /* argv[1] is the program; &argv[1] is its (NULL-terminated) argv. Inherit our fds
     * and environment so the child behaves exactly as if the supervisor spawned it. */
    int rc = posix_spawn(&pid, argv[1], NULL, &attrs, &argv[1], environ);
    posix_spawnattr_destroy(&attrs);
    if (rc != 0) {
        fprintf(stderr, "tcc-disclaim: spawn '%s' failed: %d\n", argv[1], rc);
        return 127;
    }
    g_child = pid;

    int status = 0;
    while (waitpid(pid, &status, 0) < 0) {
        /* EINTR from a signal we just forwarded — keep waiting for the real exit. */
    }
    if (WIFEXITED(status)) {
        return WEXITSTATUS(status);
    }
    if (WIFSIGNALED(status)) {
        return 128 + WTERMSIG(status);
    }
    return 0;
}
