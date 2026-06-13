/* shaper — the ECHO packet-shaper op whitelist + FAIL-OPEN no-op executor (A1 skeleton).
 * The method->op table is the only place free-form wire strings meet the structured A1 enum
 * (EP-2); anything off it is SHAPER_OP_UNKNOWN, refused. THIS slice ships ZERO packet effect
 * (§4): shaper_execute logs intent and reports a no-op — no pf, no BPF, no root. The real
 * effects land one slice at a time, on a throwaway anchor, with per-command root approval. */
#include "shaper.h"

#include <stddef.h>
#include <stdio.h>
#include <string.h>

/* Whitelist: op enum <-> canonical wire method name. Indexed by shaper_op_t. */
static const char *const OP_NAMES[] = {
    [SHAPER_OP_UNKNOWN] = NULL,
    [SHAPER_OP_ANCHOR_LOAD] = "shaper.anchor.load",
    [SHAPER_OP_PACE] = "shaper.pace",
    [SHAPER_OP_ANCHOR_REMOVE] = "shaper.anchor.remove",
};

shaper_op_t shaper_op_from_method(const char *method) {
    if (method == NULL) {
        return SHAPER_OP_UNKNOWN;
    }
    for (shaper_op_t op = SHAPER_OP_ANCHOR_LOAD; op <= SHAPER_OP_ANCHOR_REMOVE; op++) {
        if (strcmp(method, OP_NAMES[op]) == 0) {
            return op;
        }
    }
    return SHAPER_OP_UNKNOWN;
}

const char *shaper_op_method_name(shaper_op_t op) {
    if (op < SHAPER_OP_ANCHOR_LOAD || op > SHAPER_OP_ANCHOR_REMOVE) {
        return NULL;
    }
    return OP_NAMES[op];
}

shaper_result_t shaper_execute(shaper_op_t op, int *did_noop) {
    const char *name = shaper_op_method_name(op);
    if (name == NULL) {
        if (did_noop != NULL) {
            *did_noop = 0;
        }
        return SHAPER_ERR_NOTFOUND;
    }
    /* A1 skeleton: NO packet effect (§4). Fail-OPEN by construction — we touch nothing, so
     * the network is undisturbed. The real pf/BPF path lands in later gated slices (EP-3). */
    fprintf(stderr, "chimera-echo-shaper: NO-OP %s (skeleton — no pf, fail-OPEN)\n", name);
    if (did_noop != NULL) {
        *did_noop = 1;
    }
    return SHAPER_OK;
}
