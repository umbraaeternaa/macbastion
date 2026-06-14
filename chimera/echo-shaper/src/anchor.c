/* anchor — ECHO's pf-anchor lifecycle (§8 Amendment A1, EP-2/EP-3). Routes outbound traffic
 * through CHIMERA's dummynet pipe at a set rate. The pf actions run through an injectable
 * backend (write_file / run / remove_file): tests record them root-free; the real default uses
 * posix_spawn pfctl/dnctl + fopen/unlink and needs root (run only with per-command approval).
 * clear() is FAIL-OPEN — it attempts every restore step so the network is always recovered. */
#include "anchor.h"

#include <errno.h>
#include <spawn.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

/* CHIMERA's dummynet pipe number (collision-unlikely). */
#define SHAPER_PIPE "1337"

extern char **environ;

/* VALIDATED anchor content (§7, Day 22) — routes BOTH directions through CHIMERA's pipe so
 * constant-rate normalization covers download (in) and upload (out); `out` alone left inbound
 * traffic unshaped (F2). The required parent `dummynet-anchor "com.chimera.echo"` hook is added
 * to the main ruleset at opt-in install time (EP-9), NOT here — at runtime we touch only this
 * anchor + the pipe. If that hook is absent the rule is simply inert (FAIL-OPEN: traffic flows). */
int shaper_anchor_build_rules(char *buf, size_t bufsz) {
    if (buf == NULL || bufsz == 0) {
        return -1;
    }
    int n = snprintf(buf, bufsz,
                     "dummynet in all pipe "  SHAPER_PIPE "\n"
                     "dummynet out all pipe " SHAPER_PIPE "\n");
    return (n > 0 && (size_t)n < bufsz) ? 0 : -1;
}

/* --- real default backend (needs root; the test runner swaps in a recording stand-in) --- */
static int real_write_file(const char *path, const char *content) {
    FILE *f = fopen(path, "w");
    if (f == NULL) {
        return -1;
    }
    int wrote_ok = (fputs(content, f) >= 0);
    int closed_ok = (fclose(f) == 0);
    return (wrote_ok && closed_ok) ? 0 : -1;
}
static int real_run(const char *const argv[]) {
    pid_t pid;
    if (posix_spawn(&pid, argv[0], NULL, NULL, (char *const *)argv, environ) != 0) {
        return -1;
    }
    int status = 0;
    if (waitpid(pid, &status, 0) < 0) {
        return -1;
    }
    return (WIFEXITED(status) && WEXITSTATUS(status) == 0) ? 0 : -1;
}
static int real_remove_file(const char *path) {
    return (unlink(path) == 0 || errno == ENOENT) ? 0 : -1;
}
static const shaper_anchor_ops_t REAL_OPS = {real_write_file, real_run, real_remove_file};
static const shaper_anchor_ops_t *g_ops = &REAL_OPS;

void shaper_anchor_set_ops(const shaper_anchor_ops_t *ops) {
    g_ops = (ops != NULL) ? ops : &REAL_OPS;
}

int shaper_anchor_apply(int rate_kbps) {
    if (rate_kbps <= 0) {
        return -1;
    }
    char rules[128];
    if (shaper_anchor_build_rules(rules, sizeof rules) != 0) {
        return -1;
    }
    char bw[32];
    snprintf(bw, sizeof bw, "%dKbit/s", rate_kbps);

    /* keys-of-the-path order: write the anchor file, configure the pipe bandwidth, load it. */
    const char *const cfg[] = {"/usr/sbin/dnctl", "pipe", SHAPER_PIPE, "config", "bw", bw, NULL};
    const char *const load[] = {"/sbin/pfctl", "-a", SHAPER_ANCHOR_NAME, "-f", SHAPER_ANCHOR_PATH,
                                NULL};
    if (g_ops->write_file(SHAPER_ANCHOR_PATH, rules) != 0) {
        return -1;
    }
    if (g_ops->run(cfg) != 0) {
        return -1;
    }
    if (g_ops->run(load) != 0) {
        return -1;
    }
    return 0;
}

int shaper_anchor_clear(void) {
    /* FAIL-OPEN (EP-3): attempt EVERY restore step regardless of individual failures, so the
     * network always returns to normal — flush the anchor, delete the pipe, remove the file. */
    const char *const flush[] = {"/sbin/pfctl", "-a", SHAPER_ANCHOR_NAME, "-F", "all", NULL};
    const char *const delpipe[] = {"/usr/sbin/dnctl", "pipe", SHAPER_PIPE, "delete", NULL};
    g_ops->run(flush);
    g_ops->run(delpipe);
    g_ops->remove_file(SHAPER_ANCHOR_PATH);
    return 0;
}
