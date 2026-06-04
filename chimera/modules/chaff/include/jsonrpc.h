/* JSON-RPC 2.0 framing for the core IPC client (§6.4). Thin cJSON wrapper. */
#ifndef CHAFF_JSONRPC_H
#define CHAFF_JSONRPC_H

#include "cJSON.h"

#include "chaff.h"

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

/* Parse one NDJSON line into a request. On CHAFF_OK, *out is owned (free with
 * jsonrpc_request_free). CHAFF_ERR_PARSE on malformed input or a missing method. */
chaff_result_t jsonrpc_parse_request(const char *line, jsonrpc_request_t **out);
void jsonrpc_request_free(jsonrpc_request_t *req);

/* Serialize a response/notification/error to a malloc'd compact JSON string
 * (caller frees). result/params are consumed (attached then freed). id is
 * duplicated, never consumed. NULL on allocation failure. */
char *jsonrpc_serialize_response(const cJSON *id, cJSON *result);
char *jsonrpc_serialize_notification(const char *method, cJSON *params);
char *jsonrpc_serialize_error(const cJSON *id, int code, const char *message, cJSON *data);

#endif /* CHAFF_JSONRPC_H */
