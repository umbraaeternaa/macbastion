/* jsonrpc — STUB (RED-B). Real cJSON parse/serialize land in GREEN. */
#include "jsonrpc.h"

chaff_result_t jsonrpc_parse_request(const char *line, jsonrpc_request_t **out) {
    (void)line;
    if (out) {
        *out = NULL;
    }
    return CHAFF_ERR_PARSE; /* TODO(green): cJSON_Parse + extract method/id/params */
}

void jsonrpc_request_free(jsonrpc_request_t *req) {
    (void)req; /* TODO(green): free method + cJSON nodes */
}

char *jsonrpc_serialize_response(const cJSON *id, cJSON *result) {
    (void)id;
    (void)result;
    return NULL; /* TODO(green): build {jsonrpc,id,result} + print */
}

char *jsonrpc_serialize_notification(const char *method, cJSON *params) {
    (void)method;
    (void)params;
    return NULL; /* TODO(green): build {jsonrpc,method,params} + print */
}

char *jsonrpc_serialize_error(const cJSON *id, int code, const char *message, cJSON *data) {
    (void)id;
    (void)code;
    (void)message;
    (void)data;
    return NULL; /* TODO(green): build {jsonrpc,id,error{code,message,data}} + print */
}
