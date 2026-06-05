/* JSON-RPC 2.0 framing (§6.4 wire format). Thin cJSON wrapper, C — the 4th copy
 * in the CHAFF→MIRROR→shim→tether lineage (TE-7b: deliberate debt; a shared
 * modules/common/ extract is a future slice). Plain C so a C++ module links it
 * via the implicit `extern "C"` of a C header included from C++. */
#ifndef TETHER_JSONRPC_H
#define TETHER_JSONRPC_H

#ifdef __cplusplus
extern "C" {
#endif

#include "cJSON.h"

#include "tether_result.h"

typedef struct {
    char *method;        /* owned */
    cJSON *id;           /* owned; NULL for a notification */
    cJSON *params;       /* owned; NULL if absent */
    int is_notification; /* 1 when the message carries no id */
} jsonrpc_request_t;

typedef enum {
    JSONRPC_INVALID = 0,
    JSONRPC_REQUEST,
    JSONRPC_RESPONSE,
    JSONRPC_NOTIFICATION,
} jsonrpc_kind_t;

jsonrpc_kind_t jsonrpc_classify(const char *line);

/* Parse one NDJSON line into a request. On TETHER_OK, *out is owned (free with
 * jsonrpc_request_free). TETHER_ERR_PARSE on malformed input or a missing method. */
tether_result_t jsonrpc_parse_request(const char *line, jsonrpc_request_t **out);
void jsonrpc_request_free(jsonrpc_request_t *req);

/* Serialize to a malloc'd compact JSON string (caller frees). result/params are
 * consumed (attached then freed). id is duplicated, never consumed. */
char *jsonrpc_serialize_response(const cJSON *id, cJSON *result);
char *jsonrpc_serialize_notification(const char *method, cJSON *params);
char *jsonrpc_serialize_error(const cJSON *id, int code, const char *message, cJSON *data);

#ifdef __cplusplus
} /* extern "C" */
#endif

#endif /* TETHER_JSONRPC_H */
