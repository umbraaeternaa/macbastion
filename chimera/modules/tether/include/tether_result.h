/* C-safe result codes for TETHER. Included by both the copied C jsonrpc.c and
 * the C++ engine (plain enum + #defines are valid in both languages), so the C
 * wire layer and the C++ logic share one definition without a C↔C++ header clash
 * (tether.hpp itself is C++-only — classes/enum class — and cannot be included
 * from C). */
#ifndef TETHER_RESULT_H
#define TETHER_RESULT_H

/* Internal return-code idiom (mirrors the CHAFF/MIRROR/shim convention). */
typedef enum {
    TETHER_OK = 0,
    TETHER_ERR = -1,          /* generic failure */
    TETHER_ERR_PARSE = -2,    /* malformed input */
    TETHER_ERR_IO = -3,       /* socket I/O */
    TETHER_ERR_NOTFOUND = -5, /* unknown method / missing entry */
} tether_result_t;

/* Wire codes — CHIMERA §6 error table (NOT generic JSON-RPC -32601):
 *   -31002 capability missing   — method not in the tether.* whitelist
 *   -31004 precondition failed  — gated method (pairing needs Keychain/TCC) */
#define TETHER_RPC_CAPABILITY_MISSING (-31002)
#define TETHER_RPC_PRECONDITION_FAILED (-31004)

#endif /* TETHER_RESULT_H */
