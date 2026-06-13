/* A1 EP-5: JSON-RPC dispatch for the shaper. Auth-first, per-boot-secret gate on the pf ops,
 * §6 error codes. Hermetic — a recording anchor backend; no root, no real pf, no socket. */
#include <stddef.h>
#include <stdlib.h>

#include "unity.h"

#include "anchor.h"
#include "cJSON.h"
#include "protocol.h"
#include "tests.h"

/* recording anchor backend: count file writes (= apply) and removes (= clear). */
static int g_writes;
static int g_removes;
static int rec_write(const char *p, const char *c) {
    (void)p;
    (void)c;
    g_writes++;
    return 0;
}
static int rec_run(const char *const argv[]) {
    (void)argv;
    return 0;
}
static int rec_remove(const char *p) {
    (void)p;
    g_removes++;
    return 0;
}
static const shaper_anchor_ops_t REC_OPS = {rec_write, rec_run, rec_remove};

static void reset(void) {
    g_writes = 0;
    g_removes = 0;
    shaper_anchor_set_ops(&REC_OPS);
}

/* --- response inspectors (parse the JSON the dispatcher returned) --- */
static int err_code(char *resp) {
    cJSON *j = cJSON_Parse(resp);
    cJSON *e = cJSON_GetObjectItem(j, "error");
    cJSON *c = cJSON_GetObjectItem(e, "code"); /* cJSON_GetObjectItem(NULL,..) -> NULL */
    int code = (c != NULL) ? c->valueint : 0;
    cJSON_Delete(j);
    return code;
}
static int result_true(char *resp, const char *key) {
    cJSON *j = cJSON_Parse(resp);
    cJSON *r = cJSON_GetObjectItem(j, "result");
    int v = cJSON_IsTrue(cJSON_GetObjectItem(r, key)) ? 1 : 0;
    cJSON_Delete(j);
    return v;
}

static cJSON *id1(void) { return cJSON_CreateNumber(1); }

static void test_unauthorized_is_refused(void) {
    reset();
    cJSON *id = id1();
    char *r = shaper_protocol_dispatch("shaper.ping", NULL, id, 0, "S3CRET");
    TEST_ASSERT_EQUAL_INT(SHAPER_RPC_NOT_AUTHORIZED, err_code(r));
    free(r);
    cJSON_Delete(id);
}

static void test_ping_authorized_pongs(void) {
    reset();
    cJSON *id = id1();
    char *r = shaper_protocol_dispatch("shaper.ping", NULL, id, 1, "S3CRET");
    TEST_ASSERT_EQUAL_INT(1, result_true(r, "pong"));
    free(r);
    cJSON_Delete(id);
}

static void test_unknown_method_capability_missing(void) {
    reset();
    cJSON *id = id1();
    char *r = shaper_protocol_dispatch("shaper.bogus", NULL, id, 1, "S3CRET");
    TEST_ASSERT_EQUAL_INT(SHAPER_RPC_CAPABILITY_MISSING, err_code(r));
    free(r);
    cJSON_Delete(id);
}

static void test_anchor_load_requires_secret(void) {
    reset();
    cJSON *id = id1();
    cJSON *p = cJSON_CreateObject();
    cJSON_AddNumberToObject(p, "rate_kbps", 100); /* NO secret */
    char *r = shaper_protocol_dispatch("shaper.anchor.load", p, id, 1, "S3CRET");
    TEST_ASSERT_EQUAL_INT(SHAPER_RPC_NOT_AUTHORIZED, err_code(r));
    TEST_ASSERT_EQUAL_INT(0, g_writes); /* anchor NOT applied without the secret */
    free(r);
    cJSON_Delete(p);
    cJSON_Delete(id);
}

static void test_anchor_load_with_secret_applies(void) {
    reset();
    cJSON *id = id1();
    cJSON *p = cJSON_CreateObject();
    cJSON_AddNumberToObject(p, "rate_kbps", 100);
    cJSON_AddStringToObject(p, "secret", "S3CRET");
    char *r = shaper_protocol_dispatch("shaper.anchor.load", p, id, 1, "S3CRET");
    TEST_ASSERT_EQUAL_INT(1, result_true(r, "ok"));
    TEST_ASSERT_EQUAL_INT(1, g_writes); /* anchor really applied via the backend */
    free(r);
    cJSON_Delete(p);
    cJSON_Delete(id);
}

static void test_anchor_remove_with_secret_clears(void) {
    reset();
    cJSON *id = id1();
    cJSON *p = cJSON_CreateObject();
    cJSON_AddStringToObject(p, "secret", "S3CRET");
    char *r = shaper_protocol_dispatch("shaper.anchor.remove", p, id, 1, "S3CRET");
    TEST_ASSERT_EQUAL_INT(1, result_true(r, "ok"));
    TEST_ASSERT_EQUAL_INT(1, g_removes); /* anchor really cleared (fail-OPEN) */
    free(r);
    cJSON_Delete(p);
    cJSON_Delete(id);
}

void run_protocol_tests(void) {
    RUN_TEST(test_unauthorized_is_refused);
    RUN_TEST(test_ping_authorized_pongs);
    RUN_TEST(test_unknown_method_capability_missing);
    RUN_TEST(test_anchor_load_requires_secret);
    RUN_TEST(test_anchor_load_with_secret_applies);
    RUN_TEST(test_anchor_remove_with_secret_clears);
}
