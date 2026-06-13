/* CHIMERA ECHO packet-shaper (§8 Amendment A1, docs/ECHO_PACKET.md). A SEPARATE root
 * LaunchDaemon — distinct from the privileged shim (§8.8, which never opens sockets) — whose
 * ONLY job is ECHO's pf-anchor lifecycle + constant-rate pacing (EP-2). THIS slice is the
 * no-op skeleton: the op whitelist + a FAIL-OPEN no-op executor that touches NOTHING (no pf,
 * no BPF, no root, §4). The real pf path lands in later gated slices, on a throwaway anchor,
 * with per-command root approval. Fail-OPEN is the law here (EP-3): a traffic component must
 * NEVER wedge the network — when in doubt it does nothing and lets real traffic flow. */
#ifndef SHAPER_H
#define SHAPER_H

/* The enumerated capability (EP-2). Anything off this list is SHAPER_OP_UNKNOWN and refused —
 * this list IS the shaper's boundary into root. */
typedef enum {
    SHAPER_OP_UNKNOWN = 0,
    SHAPER_OP_ANCHOR_LOAD,    /* load/refresh ECHO's pf anchor with the current rate */
    SHAPER_OP_PACE,           /* run the constant-rate pacer over that anchor */
    SHAPER_OP_ANCHOR_REMOVE   /* remove the anchor + stop pacing (restore normal flow) */
} shaper_op_t;

/* Op result. */
typedef enum {
    SHAPER_OK = 0,
    SHAPER_ERR = -1,
    SHAPER_ERR_NOTFOUND = -2  /* SHAPER_OP_UNKNOWN — method not whitelisted */
} shaper_result_t;

/* Map a shaper.* method string to an op enum; SHAPER_OP_UNKNOWN if not whitelisted. */
shaper_op_t shaper_op_from_method(const char *method);

/* The canonical wire method name for an op (e.g. "shaper.anchor.load"), or NULL for UNKNOWN. */
const char *shaper_op_method_name(shaper_op_t op);

/* Execute an op. THIS slice: every known op is a FAIL-OPEN no-op — it touches no pf/packets,
 * sets *did_noop to 1, and returns SHAPER_OK. SHAPER_OP_UNKNOWN returns SHAPER_ERR_NOTFOUND
 * (and *did_noop = 0). `did_noop` may be NULL. */
shaper_result_t shaper_execute(shaper_op_t op, int *did_noop);

#endif /* SHAPER_H */
