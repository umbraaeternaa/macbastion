/* PURGE config core — post-purge action + tamper-evident marker (§7/§4/§8, PC-1…3).
 * Pure, no I/O (persistence + IPC live in later slices). */
#include <stddef.h>
#include <string.h>

#include "config.h"

purge_config_t purge_config_default(void) {
    purge_config_t c = {PURGE_REBOOT, 0};
    return c;
}

int purge_post_action_from_str(const char *s) {
    if (s == NULL) {
        return -1;
    }
    if (strcmp(s, "reboot") == 0) {
        return PURGE_REBOOT;
    }
    if (strcmp(s, "shutdown") == 0) {
        return PURGE_SHUTDOWN;
    }
    if (strcmp(s, "stay") == 0) {
        return PURGE_STAY;
    }
    return -1;
}

const char *purge_post_action_str(purge_post_action_t a) {
    switch (a) {
        case PURGE_REBOOT:
            return "reboot";
        case PURGE_SHUTDOWN:
            return "shutdown";
        case PURGE_STAY:
            return "stay";
    }
    return "?";
}

int purge_config_set(purge_config_t *cfg, const char *post_action, const int *marker) {
    if (cfg == NULL) {
        return -1;
    }
    /* Validate the post_action BEFORE mutating, so a bad value leaves cfg untouched. */
    purge_post_action_t new_action = cfg->post_action;
    if (post_action != NULL) {
        int parsed = purge_post_action_from_str(post_action);
        if (parsed < 0) {
            return -1;
        }
        new_action = (purge_post_action_t)parsed;
    }
    cfg->post_action = new_action;
    if (marker != NULL) {
        cfg->marker = *marker ? 1 : 0;
    }
    return 0;
}
