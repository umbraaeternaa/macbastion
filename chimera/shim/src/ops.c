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

#include <stddef.h>
#include <stdio.h>
#include <string.h>

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
    /* Slice 1: log intent, perform NO real effect (F3). Real ops are Slice 3+. */
    fprintf(stderr, "chimera-shim: NO-OP %s (skeleton — no real effect)\n", name);
    if (did_noop) {
        *did_noop = 1;
    }
    return SHIM_OK;
}
