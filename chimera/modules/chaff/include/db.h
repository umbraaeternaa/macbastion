/* SQLite storage: config + generation log (§5.1). Profile tables (Phase A)
 * are deferred — only config/state + generation log are used in Phase B. */
#ifndef CHAFF_DB_H
#define CHAFF_DB_H

#include <stddef.h>
#include <stdint.h>

#include <sqlite3.h>

#include "chaff.h"

/* Open a database (":memory:" supported). On CHAFF_OK, *out is owned. */
chaff_result_t db_open(const char *path, sqlite3 **out);

/* Create tables if absent. Idempotent. */
chaff_result_t db_init_schema(sqlite3 *db);

/* Record one generated decoy request. */
chaff_result_t db_insert_generation(sqlite3 *db, const char *endpoint, int64_t ts, int status);

/* Count rows in the generation log. */
chaff_result_t db_count_generation(sqlite3 *db, int64_t *out_count);

void db_close(sqlite3 *db);

#endif /* CHAFF_DB_H */
