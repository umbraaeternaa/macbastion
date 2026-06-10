/* ops — the 4-op whitelist and its Slice 1 NO-OP executor.
 *
 * The method↔op table is the only place free-form wire strings meet the
 * structured §8.8 enum (SH-5 (c)); anything not in it is SHIM_OP_UNKNOWN and is
 * refused upstream (-31002).
 *
 * Slice 1: ops_execute has ZERO destructive effect (F3) — it logs the intent and
 * reports a no-op. The real effects (lock / evict / reboot / killall) land one at
 * a time in Slice 3+, destructive ones last and only once the per-boot secret is
 * real (§5.4). reboot stays stubbed in autotests forever (SH-11). */
#include "ops.h"

#include <spawn.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>

extern char **environ;

/* Slice 3a: the real lock — sleep the display via pmset. With "require password after
 * sleep" this locks the screen (§8.8 lock / screensaver). Root-direct; no GUI-session
 * gymnastics. NEVER invoked in autotests (the test runner swaps in a safe stand-in). */
static shim_result_t lock_screen_real(void) {
    char *const argv[] = {"/usr/bin/pmset", "displaysleepnow", NULL};
    pid_t pid;
    if (posix_spawn(&pid, "/usr/bin/pmset", NULL, NULL, argv, environ) != 0) {
        return SHIM_ERR;
    }
    int status = 0;
    if (waitpid(pid, &status, 0) < 0) {
        return SHIM_ERR;
    }
    return (WIFEXITED(status) && WEXITSTATUS(status) == 0) ? SHIM_OK : SHIM_ERR;
}

static ops_lock_fn g_lock = lock_screen_real;

ops_lock_fn ops_set_lock_action(ops_lock_fn fn) {
    ops_lock_fn prev = g_lock;
    g_lock = fn ? fn : lock_screen_real;
    return prev;
}

/* Whitelist: op enum ↔ canonical wire method name. Indexed by shim_op_t. */
static const char *const OP_NAMES[] = {
    [SHIM_OP_UNKNOWN] = NULL,
    [SHIM_OP_LOCK] = "shim.lock",
    [SHIM_OP_EVICT] = "shim.evict",
    [SHIM_OP_REBOOT] = "shim.reboot",
    [SHIM_OP_KILLALL] = "shim.killall",
};

shim_op_t ops_from_method(const char *method) {
    if (!method) {
        return SHIM_OP_UNKNOWN;
    }
    for (shim_op_t op = SHIM_OP_LOCK; op <= SHIM_OP_KILLALL; op++) {
        if (strcmp(method, OP_NAMES[op]) == 0) {
            return op;
        }
    }
    return SHIM_OP_UNKNOWN;
}

const char *ops_method_name(shim_op_t op) {
    if (op < SHIM_OP_LOCK || op > SHIM_OP_KILLALL) {
        return NULL;
    }
    return OP_NAMES[op];
}

shim_result_t ops_execute(shim_op_t op, int *did_noop) {
    const char *name = ops_method_name(op);
    if (!name) {
        if (did_noop) {
            *did_noop = 0;
        }
        return SHIM_ERR_NOTFOUND;
    }
    /* Slice 3a: LOCK is real (the reversible operator command) — run the lock action. */
    if (op == SHIM_OP_LOCK) {
        if (did_noop) {
            *did_noop = 0;
        }
        return g_lock();
    }
    /* evict / reboot / killall: still logged no-ops until their own slices (3b+). */
    fprintf(stderr, "chimera-shim: NO-OP %s (real effect lands in a later slice)\n", name);
    if (did_noop) {
        *did_noop = 1;
    }
    return SHIM_OK;
}
