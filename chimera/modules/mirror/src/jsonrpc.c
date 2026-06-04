/* jsonrpc — JSON-RPC 2.0 framing over cJSON (§6.4). */
#include "jsonrpc.h"

#include <stdlib.h>
#include <string.h>

static char *dupstr(const char *s) {
    if (!s) {
        return NULL;
    }
    size_t n = strlen(s) + 1;
    char *p = malloc(n);
    if (p) {
        memcpy(p, s, n);
    }
    return p;
}

jsonrpc_kind_t jsonrpc_classify(const char *line) {
    if (!line) {
        return JSONRPC_INVALID;
    }
    cJSON *root = cJSON_Parse(line);
    if (!root) {
        return JSONRPC_INVALID;
    }
    int has_method = cJSON_GetObjectItemCaseSensitive(root, "method") != NULL;
    int has_id = cJSON_GetObjectItemCaseSensitive(root, "id") != NULL;
    int has_payload = cJSON_GetObjectItemCaseSensitive(root, "result") != NULL ||
                      cJSON_GetObjectItemCaseSensitive(root, "error") != NULL;
    jsonrpc_kind_t kind;
    if (has_method && has_id) {
        kind = JSONRPC_REQUEST;
    } else if (has_method) {
        kind = JSONRPC_NOTIFICATION;
    } else if (has_payload) {
        kind = JSONRPC_RESPONSE;
    } else {
        kind = JSONRPC_INVALID;
    }
    cJSON_Delete(root);
    return kind;
}

mirror_result_t jsonrpc_parse_request(const char *line, jsonrpc_request_t **out) {
    if (!line || !out) {
        return MIRROR_ERR;
    }
    *out = NULL;
    cJSON *root = cJSON_Parse(line);
    if (!root) {
        return MIRROR_ERR_PARSE;
    }
    cJSON *method = cJSON_GetObjectItemCaseSensitive(root, "method");
    if (!cJSON_IsString(method)) {
        cJSON_Delete(root);
        return MIRROR_ERR_PARSE;
    }
    jsonrpc_request_t *req = calloc(1, sizeof(*req));
    if (!req) {
        cJSON_Delete(root);
        return MIRROR_ERR;
    }
    req->method = dupstr(method->valuestring);
    if (!req->method) {
        free(req);
        cJSON_Delete(root);
        return MIRROR_ERR;
    }
    cJSON *id = cJSON_GetObjectItemCaseSensitive(root, "id");
    if (id) {
        req->id = cJSON_Duplicate(id, 1);
        req->is_notification = 0;
    } else {
        req->id = NULL;
        req->is_notification = 1;
    }
    cJSON *params = cJSON_GetObjectItemCaseSensitive(root, "params");
    if (params) {
        req->params = cJSON_Duplicate(params, 1);
    }
    cJSON_Delete(root);
    *out = req;
    return MIRROR_OK;
}

void jsonrpc_request_free(jsonrpc_request_t *req) {
    if (!req) {
        return;
    }
    free(req->method);
    if (req->id) {
        cJSON_Delete(req->id);
    }
    if (req->params) {
        cJSON_Delete(req->params);
    }
    free(req);
}

char *jsonrpc_serialize_response(const cJSON *id, cJSON *result) {
    cJSON *root = cJSON_CreateObject();
    if (!root) {
        if (result) {
            cJSON_Delete(result);
        }
        return NULL;
    }
    cJSON_AddStringToObject(root, "jsonrpc", "2.0");
    cJSON_AddItemToObject(root, "id", id ? cJSON_Duplicate(id, 1) : cJSON_CreateNull());
    cJSON_AddItemToObject(root, "result", result ? result : cJSON_CreateNull());
    char *s = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    return s;
}

char *jsonrpc_serialize_notification(const char *method, cJSON *params) {
    cJSON *root = cJSON_CreateObject();
    if (!root) {
        if (params) {
            cJSON_Delete(params);
        }
        return NULL;
    }
    cJSON_AddStringToObject(root, "jsonrpc", "2.0");
    cJSON_AddStringToObject(root, "method", method ? method : "");
    cJSON_AddItemToObject(root, "params", params ? params : cJSON_CreateNull());
    char *s = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    return s;
}

char *jsonrpc_serialize_error(const cJSON *id, int code, const char *message, cJSON *data) {
    cJSON *root = cJSON_CreateObject();
    if (!root) {
        if (data) {
            cJSON_Delete(data);
        }
        return NULL;
    }
    cJSON_AddStringToObject(root, "jsonrpc", "2.0");
    cJSON_AddItemToObject(root, "id", id ? cJSON_Duplicate(id, 1) : cJSON_CreateNull());
    cJSON *err = cJSON_CreateObject();
    cJSON_AddNumberToObject(err, "code", code);
    cJSON_AddStringToObject(err, "message", message ? message : "");
    if (data) {
        cJSON_AddItemToObject(err, "data", data);
    }
    cJSON_AddItemToObject(root, "error", err);
    char *s = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    return s;
}
