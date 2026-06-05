/* ops — the 4-op whitelist and its Slice 1 NO-OP executor.
 *
 * RED STUB (Slice 1): every function is unimplemented —
 *   - ops_from_method  maps nothing (always SHIM_OP_UNKNOWN)
 *   - ops_method_name  returns NULL
 *   - ops_execute      errors (no no-op result yet)
 * GREEN fills the method↔op table and the logged-no-op executor. The real
 * destructive effects remain absent until Slice 3+ (reboot never in autotests,
 * SH-11). */
#include "ops.h"

#include <stddef.h>

shim_op_t ops_from_method(const char *method) {
    (void)method; /* RED: GREEN matches shim.{lock,evict,reboot,killall}. */
    return SHIM_OP_UNKNOWN;
}

const char *ops_method_name(shim_op_t op) {
    (void)op; /* RED: GREEN returns the canonical "shim.*" name. */
    return NULL;
}

shim_result_t ops_execute(shim_op_t op, int *did_noop) {
    (void)op; /* RED: GREEN logs intent and sets *did_noop = 1. */
    if (did_noop) {
        *did_noop = 0;
    }
    return SHIM_ERR;
}
