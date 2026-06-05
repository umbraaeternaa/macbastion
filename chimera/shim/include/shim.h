/* CHIMERA privileged shim (§8.8 / §7.10). Umbrella header: version, internal
 * result codes, wire-facing JSON-RPC error codes, and the 4-op enum.
 *
 * Slice 1 scope (SHIM.md §5.4): a NO-OP security skeleton. The socket server,
 * LOCAL_PEERCRED peer check, op-enum whitelist and ping/pong are real; every
 * privileged effect (lock / evict / reboot / killall) is a logged no-op stub
 * (F3 — zero destructive effect). The per-boot secret (Slice 2) and the real
 * ops (Slice 3+) are deliberately absent. (MANIFESTO §4 — honest accounting.) */
#ifndef SHIM_H
#define SHIM_H

#define SHIM_VERSION "0.1.0-alpha"

/* Internal return-code idiom (mirrors the CHAFF/MIRROR convention). Wire-facing
 * JSON-RPC codes below are emitted only by the protocol/dispatch layer. */
typedef enum {
    SHIM_OK = 0,
    SHIM_ERR = -1,          /* generic failure */
    SHIM_ERR_PARSE = -2,    /* malformed input */
    SHIM_ERR_IO = -3,       /* socket I/O */
    SHIM_ERR_AUTH = -4,     /* peer credential mismatch */
    SHIM_ERR_NOTFOUND = -5, /* unknown op / missing entry */
} shim_result_t;

/* Wire codes — CHIMERA §6 error table (NOT generic JSON-RPC -32601):
 *   -31007 not authorized   — peer uid is not the operator (peercred reject)
 *   -31002 capability missing — method is not in the 4-op whitelist / disabled */
#define SHIM_RPC_NOT_AUTHORIZED (-31007)
#define SHIM_RPC_CAPABILITY_MISSING (-31002)

/* The enumerated privileged operations. This list IS the §8.8 security boundary
 * into root; any addition requires a §8 amendment, not a code change. Slice 1
 * executes all of them as no-ops. */
typedef enum {
    SHIM_OP_UNKNOWN = 0, /* not in the whitelist */
    SHIM_OP_LOCK,        /* lock screen / activate screensaver  (TETHER L1, operator) */
    SHIM_OP_EVICT,       /* evict CHIMERA Keychain items        (PURGE Tier 0) */
    SHIM_OP_REBOOT,      /* force-reboot                        (PURGE post-action) */
    SHIM_OP_KILLALL,     /* force-killall on shutdown timeout   (core §7.7) */
} shim_op_t;

#endif /* SHIM_H */
