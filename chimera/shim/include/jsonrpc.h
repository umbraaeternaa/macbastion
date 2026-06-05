/* JSON-RPC 2.0 framing for the privileged shim socket (§6.4 wire format, reused
 * per SH-2). Thin cJSON wrapper, copied from the CHAFF/MIRROR lineage. */
#ifndef SHIM_JSONRPC_H
#define SHIM_JSONRPC_H

#include "cJSON.h"

#include "shim.h"

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

/* Parse one NDJSON line into a request. On SHIM_OK, *out is owned (free with
 * jsonrpc_request_free). SHIM_ERR_PARSE on malformed input or a missing method. */
shim_result_t jsonrpc_parse_request(const char *line, jsonrpc_request_t **out);
void jsonrpc_request_free(jsonrpc_request_t *req);

/* Serialize to a malloc'd compact JSON string (caller frees). result/params are
 * consumed (attached then freed). id is duplicated, never consumed. */
char *jsonrpc_serialize_response(const cJSON *id, cJSON *result);
char *jsonrpc_serialize_notification(const char *method, cJSON *params);
char *jsonrpc_serialize_error(const cJSON *id, int code, const char *message, cJSON *data);

#endif /* SHIM_JSONRPC_H */
