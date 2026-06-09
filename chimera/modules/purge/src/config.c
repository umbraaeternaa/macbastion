/* PURGE config core — RED stub (PC-5). Sentinel returns so the Unity contract fails until
 * GREEN; an honest empty stub (MANIFESTO §4). */
#include "config.h"

purge_config_t purge_config_default(void) {
    purge_config_t c = {(purge_post_action_t)(-1), -1};
    return c;
}

int purge_post_action_from_str(const char *s) {
    (void)s;
    return -42;
}

const char *purge_post_action_str(purge_post_action_t a) {
    (void)a;
    return "STUB";
}

int purge_config_set(purge_config_t *cfg, const char *post_action, const int *marker) {
    (void)cfg;
    (void)post_action;
    (void)marker;
    return -42;
}
