/* Contract for event payload builders (§6.6). RED: events.cpp builders return
 * nullptr, so payload cases fail. The wire-string helpers (stage_name /
 * disappearance_name) are REAL plumbing → green by design. */
#include "unity.h"

#include "cJSON.h"

#include "events.hpp"

using tether::Disappearance;
using tether::Stage;

/* Green by design — real string mappings, not RED logic. */
static void test_stage_name_strings(void) {
    TEST_ASSERT_EQUAL_STRING("L1", tether::stage_name(Stage::L1));
    TEST_ASSERT_EQUAL_STRING("L2", tether::stage_name(Stage::L2));
    TEST_ASSERT_EQUAL_STRING("L3", tether::stage_name(Stage::L3));
}

static void test_disappearance_name_strings(void) {
    TEST_ASSERT_EQUAL_STRING("fade", tether::disappearance_name(Disappearance::FADE));
    TEST_ASSERT_EQUAL_STRING("clean_drop", tether::disappearance_name(Disappearance::CLEAN_DROP));
    TEST_ASSERT_EQUAL_STRING("instant_drop",
                             tether::disappearance_name(Disappearance::INSTANT_DROP));
}

static void test_present_payload(void) {
    cJSON *p = tether::event_present(-50.0);
    TEST_ASSERT_NOT_NULL(p);
    cJSON *r = cJSON_GetObjectItemCaseSensitive(p, "rssi_smoothed");
    TEST_ASSERT_TRUE(cJSON_IsNumber(r));
    TEST_ASSERT_DOUBLE_WITHIN(0.001, -50.0, r->valuedouble);
    cJSON_Delete(p);
}

static void test_absent_payload_has_class(void) {
    cJSON *p = tether::event_absent(123, -90.0, Disappearance::INSTANT_DROP);
    TEST_ASSERT_NOT_NULL(p);
    cJSON *c = cJSON_GetObjectItemCaseSensitive(p, "disappearance_class");
    TEST_ASSERT_TRUE(cJSON_IsString(c));
    TEST_ASSERT_EQUAL_STRING("instant_drop", c->valuestring);
    cJSON_Delete(p);
}

static void test_escalation_payload_has_stage(void) {
    cJSON *p = tether::event_escalation(Stage::L1, "lock_screen", 5000);
    TEST_ASSERT_NOT_NULL(p);
    cJSON *s = cJSON_GetObjectItemCaseSensitive(p, "stage");
    TEST_ASSERT_TRUE(cJSON_IsString(s));
    TEST_ASSERT_EQUAL_STRING("L1", s->valuestring);
    cJSON_Delete(p);
}

static void test_recovered_payload(void) {
    cJSON *p = tether::event_recovered(Stage::L2, -40.0);
    TEST_ASSERT_NOT_NULL(p);
    cJSON_Delete(p);
}

void run_emit_tests(void) {
    RUN_TEST(test_stage_name_strings);
    RUN_TEST(test_disappearance_name_strings);
    RUN_TEST(test_present_payload);
    RUN_TEST(test_absent_payload_has_class);
    RUN_TEST(test_escalation_payload_has_stage);
    RUN_TEST(test_recovered_payload);
}
