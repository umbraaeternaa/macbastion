/* db — SQLite storage: generation_log + config (§5.1). */
#include "db.h"

chaff_result_t db_open(const char *path, sqlite3 **out) {
    if (!path || !out) {
        return CHAFF_ERR;
    }
    sqlite3 *db = NULL;
    if (sqlite3_open(path, &db) != SQLITE_OK) {
        sqlite3_close(db);
        *out = NULL;
        return CHAFF_ERR_IO;
    }
    *out = db;
    return CHAFF_OK;
}

chaff_result_t db_init_schema(sqlite3 *db) {
    if (!db) {
        return CHAFF_ERR;
    }
    static const char *SQL =
        "CREATE TABLE IF NOT EXISTS generation_log ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  endpoint TEXT NOT NULL,"
        "  ts INTEGER NOT NULL,"
        "  status INTEGER NOT NULL);"
        "CREATE TABLE IF NOT EXISTS config ("
        "  key TEXT PRIMARY KEY,"
        "  value TEXT);";
    char *err = NULL;
    if (sqlite3_exec(db, SQL, NULL, NULL, &err) != SQLITE_OK) {
        sqlite3_free(err);
        return CHAFF_ERR_IO;
    }
    return CHAFF_OK;
}

chaff_result_t db_insert_generation(sqlite3 *db, const char *endpoint, int64_t ts, int status) {
    if (!db || !endpoint) {
        return CHAFF_ERR;
    }
    sqlite3_stmt *stmt = NULL;
    static const char *SQL = "INSERT INTO generation_log(endpoint, ts, status) VALUES(?,?,?);";
    if (sqlite3_prepare_v2(db, SQL, -1, &stmt, NULL) != SQLITE_OK) {
        return CHAFF_ERR_IO;
    }
    sqlite3_bind_text(stmt, 1, endpoint, -1, SQLITE_TRANSIENT);
    sqlite3_bind_int64(stmt, 2, ts);
    sqlite3_bind_int(stmt, 3, status);
    int rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);
    return (rc == SQLITE_DONE) ? CHAFF_OK : CHAFF_ERR_IO;
}

chaff_result_t db_count_generation(sqlite3 *db, int64_t *out_count) {
    if (!db || !out_count) {
        return CHAFF_ERR;
    }
    sqlite3_stmt *stmt = NULL;
    if (sqlite3_prepare_v2(db, "SELECT COUNT(*) FROM generation_log;", -1, &stmt, NULL) !=
        SQLITE_OK) {
        return CHAFF_ERR_IO;
    }
    chaff_result_t res = CHAFF_ERR_IO;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        *out_count = sqlite3_column_int64(stmt, 0);
        res = CHAFF_OK;
    }
    sqlite3_finalize(stmt);
    return res;
}

void db_close(sqlite3 *db) {
    if (db) {
        sqlite3_close(db);
    }
}
