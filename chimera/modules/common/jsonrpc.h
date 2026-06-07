/* JSON-RPC 2.0 framing for the core IPC client (§6.4). Thin cJSON wrapper.
 *
 * The SHARED CHIMERA jsonrpc — the canonical single-contract extract (JE-1/JE-2).
 * It replaces the four byte-identical per-module copies (chaff -> mirror -> shim ->
 * tether), whose only divergence was the namespaced result type. One true
 * jsonrpc_result_t ends that drift.
 *
 * Consumers supply cJSON on the include path (e.g. -Isrc/vendor/cjson); this
 * header stays cJSON-location-agnostic. The extern "C" guard lets the C++ module
 * (tether) link this C translation unit. */
#ifndef CHIMERA_JSONRPC_H
#define CHIMERA_JSONRPC_H

#include "cJSON.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Parse outcome. Canonical replacement for the per-module <MOD>_result_t triplet
 * (OK=0 / ERR=-1 / ERR_PARSE=-2), which was identical across all four copies —
 * this IS that one contract. OK is 0, the only value any call site compares. */
typedef enum {
    JSONRPC_OK = 0,
    JSONRPC_ERR = -1,       /* generic failure */
    JSONRPC_ERR_PARSE = -2, /* malformed input or a missing method */
} jsonrpc_result_t;

typedef struct {
    char *method;        /* owned */
    cJSON *id;           /* owned; NULL for a notification */
    cJSON *params;       /* owned; NULL if absent */
    int is_notification; /* 1 when the message carries no id */
} jsonrpc_request_t;

/* Frame classification for the daemon's inbound demux: a routed command
 * (REQUEST), an ack to one of our own core.* calls (RESPONSE), an event/
 * fire-and-forget (NOTIFICATION), or unparseable (INVALID). */
typedef enum {
    JSONRPC_INVALID = 0,
    JSONRPC_REQUEST,
    JSONRPC_RESPONSE,
    JSONRPC_NOTIFICATION,
} jsonrpc_kind_t;

jsonrpc_kind_t jsonrpc_classify(const char *line);

/* Parse one NDJSON line into a request. On JSONRPC_OK, *out is owned (free with
 * jsonrpc_request_free). JSONRPC_ERR_PARSE on malformed input or a missing method. */
jsonrpc_result_t jsonrpc_parse_request(const char *line, jsonrpc_request_t **out);
void jsonrpc_request_free(jsonrpc_request_t *req);

/* Serialize a response/notification/error to a malloc'd compact JSON string
 * (caller frees). result/params are consumed (attached then freed). id is
 * duplicated, never consumed. NULL on allocation failure. */
char *jsonrpc_serialize_response(const cJSON *id, cJSON *result);
char *jsonrpc_serialize_notification(const char *method, cJSON *params);
char *jsonrpc_serialize_error(const cJSON *id, int code, const char *message, cJSON *data);

#ifdef __cplusplus
} /* extern "C" */
#endif

#endif /* CHIMERA_JSONRPC_H */
