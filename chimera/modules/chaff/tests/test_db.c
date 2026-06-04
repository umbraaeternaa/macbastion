/* RED-B contract for the SQLite layer (:memory:, Sub-D3). Fails until GREEN. */
#include "unity.h"

#include "db.h"

static void test_open_memory_ok(void) {
    sqlite3 *db = NULL;
    TEST_ASSERT_EQUAL_INT(CHAFF_OK, db_open(":memory:", &db));
    TEST_ASSERT_NOT_NULL(db);
    db_close(db);
}

static void test_init_schema_ok(void) {
    sqlite3 *db = NULL;
    db_open(":memory:", &db);
    TEST_ASSERT_EQUAL_INT(CHAFF_OK, db_init_schema(db));
    db_close(db);
}

static void test_init_schema_idempotent(void) {
    sqlite3 *db = NULL;
    db_open(":memory:", &db);
    TEST_ASSERT_EQUAL_INT(CHAFF_OK, db_init_schema(db));
    TEST_ASSERT_EQUAL_INT(CHAFF_OK, db_init_schema(db)); /* second call must not fail */
    db_close(db);
}

static void test_insert_ok(void) {
    sqlite3 *db = NULL;
    db_open(":memory:", &db);
    db_init_schema(db);
    TEST_ASSERT_EQUAL_INT(CHAFF_OK, db_insert_generation(db, "https://a.com", 1000, 200));
    db_close(db);
}

static void test_count_empty_is_zero(void) {
    sqlite3 *db = NULL;
    db_open(":memory:", &db);
    db_init_schema(db);
    int64_t n = -1;
    TEST_ASSERT_EQUAL_INT(CHAFF_OK, db_count_generation(db, &n));
    TEST_ASSERT_EQUAL_INT64(0, n);
    db_close(db);
}

static void test_count_after_inserts(void) {
    sqlite3 *db = NULL;
    db_open(":memory:", &db);
    db_init_schema(db);
    db_insert_generation(db, "https://a.com", 1000, 200);
    db_insert_generation(db, "https://b.com", 1001, 200);
    int64_t n = -1;
    TEST_ASSERT_EQUAL_INT(CHAFF_OK, db_count_generation(db, &n));
    TEST_ASSERT_EQUAL_INT64(2, n);
    db_close(db);
}

void run_db_tests(void) {
    RUN_TEST(test_open_memory_ok);
    RUN_TEST(test_init_schema_ok);
    RUN_TEST(test_init_schema_idempotent);
    RUN_TEST(test_insert_ok);
    RUN_TEST(test_count_empty_is_zero);
    RUN_TEST(test_count_after_inserts);
}
