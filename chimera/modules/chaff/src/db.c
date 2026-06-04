/* db — STUB (RED-B). Real SQLite open/schema/insert/count land in GREEN. */
#include "db.h"

chaff_result_t db_open(const char *path, sqlite3 **out) {
    (void)path;
    if (out) {
        *out = NULL;
    }
    return CHAFF_ERR_IO; /* TODO(green): sqlite3_open */
}

chaff_result_t db_init_schema(sqlite3 *db) {
    (void)db;
    return CHAFF_ERR_IO; /* TODO(green): CREATE TABLE IF NOT EXISTS ... */
}

chaff_result_t db_insert_generation(sqlite3 *db, const char *endpoint, int64_t ts, int status) {
    (void)db;
    (void)endpoint;
    (void)ts;
    (void)status;
    return CHAFF_ERR_IO; /* TODO(green): prepared INSERT */
}

chaff_result_t db_count_generation(sqlite3 *db, int64_t *out_count) {
    (void)db;
    if (out_count) {
        *out_count = -1;
    }
    return CHAFF_ERR_IO; /* TODO(green): SELECT COUNT(*) */
}

void db_close(sqlite3 *db) {
    (void)db; /* TODO(green): sqlite3_close */
}
