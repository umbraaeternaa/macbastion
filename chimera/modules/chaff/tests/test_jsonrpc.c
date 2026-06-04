/* RED-B contract for JSON-RPC framing. Fails against the stubs until GREEN. */
#include "unity.h"

#include <stdlib.h>
#include <string.h>

#include "jsonrpc.h"

static void test_parse_request_ok(void) {
    jsonrpc_request_t *req = NULL;
    const char *line = "{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"chaff.status\"}";
    TEST_ASSERT_EQUAL_INT(CHAFF_OK, jsonrpc_parse_request(line, &req));
    TEST_ASSERT_NOT_NULL(req);
    TEST_ASSERT_EQUAL_STRING("chaff.status", req->method);
    jsonrpc_request_free(req);
}

static void test_parse_request_has_id(void) {
    jsonrpc_request_t *req = NULL;
    const char *line = "{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"chaff.status\"}";
    jsonrpc_parse_request(line, &req);
    TEST_ASSERT_NOT_NULL(req);
    TEST_ASSERT_FALSE(req->is_notification);
    TEST_ASSERT_NOT_NULL(req->id);
    jsonrpc_request_free(req);
}

static void test_parse_notification_no_id(void) {
    jsonrpc_request_t *req = NULL;
    const char *line = "{\"jsonrpc\":\"2.0\",\"method\":\"chaff.tick\"}";
    TEST_ASSERT_EQUAL_INT(CHAFF_OK, jsonrpc_parse_request(line, &req));
    TEST_ASSERT_NOT_NULL(req);
    TEST_ASSERT_TRUE(req->is_notification);
    jsonrpc_request_free(req);
}

static void test_parse_non_json_errors(void) {
    jsonrpc_request_t *req = NULL;
    TEST_ASSERT_EQUAL_INT(CHAFF_ERR_PARSE, jsonrpc_parse_request("not json", &req));
}

static void test_parse_missing_method_errors(void) {
    jsonrpc_request_t *req = NULL;
    const char *line = "{\"jsonrpc\":\"2.0\",\"id\":1}";
    TEST_ASSERT_EQUAL_INT(CHAFF_ERR_PARSE, jsonrpc_parse_request(line, &req));
}

static void test_serialize_response_round_trips(void) {
    cJSON *id = cJSON_CreateNumber(42);
    cJSON *result = cJSON_CreateObject();
    cJSON_AddBoolToObject(result, "ok", 1);
    char *out = jsonrpc_serialize_response(id, result);
    TEST_ASSERT_NOT_NULL(out);
    cJSON *parsed = cJSON_Parse(out);
    TEST_ASSERT_NOT_NULL(parsed);
    cJSON *pid = cJSON_GetObjectItem(parsed, "id");
    TEST_ASSERT_NOT_NULL(pid);
    TEST_ASSERT_EQUAL_INT(42, pid->valueint);
    cJSON_Delete(parsed);
    cJSON_Delete(id);
    free(out);
}

static void test_serialize_notification_shape(void) {
    cJSON *params = cJSON_CreateObject();
    cJSON_AddStringToObject(params, "endpoint", "https://a.com");
    char *out = jsonrpc_serialize_notification("chaff.request.sent", params);
    TEST_ASSERT_NOT_NULL(out);
    cJSON *parsed = cJSON_Parse(out);
    TEST_ASSERT_NOT_NULL(parsed);
    cJSON *m = cJSON_GetObjectItem(parsed, "method");
    TEST_ASSERT_NOT_NULL(m);
    TEST_ASSERT_EQUAL_STRING("chaff.request.sent", m->valuestring);
    cJSON_Delete(parsed);
    free(out);
}

static void test_classify_request(void) {
    TEST_ASSERT_EQUAL_INT(JSONRPC_REQUEST,
                          jsonrpc_classify("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"x\"}"));
}

static void test_classify_response(void) {
    TEST_ASSERT_EQUAL_INT(JSONRPC_RESPONSE,
                          jsonrpc_classify("{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{}}"));
}

static void test_classify_notification(void) {
    TEST_ASSERT_EQUAL_INT(JSONRPC_NOTIFICATION,
                          jsonrpc_classify("{\"jsonrpc\":\"2.0\",\"method\":\"evt\"}"));
}

void run_jsonrpc_tests(void) {
    RUN_TEST(test_parse_request_ok);
    RUN_TEST(test_parse_request_has_id);
    RUN_TEST(test_parse_notification_no_id);
    RUN_TEST(test_parse_non_json_errors);
    RUN_TEST(test_parse_missing_method_errors);
    RUN_TEST(test_serialize_response_round_trips);
    RUN_TEST(test_serialize_notification_shape);
    RUN_TEST(test_classify_request);
    RUN_TEST(test_classify_response);
    RUN_TEST(test_classify_notification);
}
