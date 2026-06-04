/* libcurl HTTPS GET wrapper for decoy generation (§5.1 Phase B). */
#ifndef CHAFF_HTTP_H
#define CHAFF_HTTP_H

#include "chaff.h"

/* Initialise/teardown libcurl global state (call once in main, before threads). */
void http_global_init(void);
void http_global_cleanup(void);

/* Blocking GET; body discarded. CHAFF_OK on a 2xx/3xx status, else CHAFF_ERR_IO. */
chaff_result_t http_get(const char *url, long timeout_s);

#endif /* CHAFF_HTTP_H */
