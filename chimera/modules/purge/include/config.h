/* PURGE config core — post-purge action + tamper-evident marker (§7/§4/§8, PC-1…3). Pure. */
#ifndef PURGE_CONFIG_H
#define PURGE_CONFIG_H

typedef enum {
    PURGE_REBOOT = 0,   /* §4 default: power-cycle to clear RAM */
    PURGE_SHUTDOWN = 1, /* end the session */
    PURGE_STAY = 2      /* stealthier, but RAM residue lingers */
} purge_post_action_t;

typedef struct {
    purge_post_action_t post_action;
    int marker; /* §8: leave a "purged at <ts>" marker? default off (deniability) */
} purge_config_t;

/* §4/§8 defaults: {PURGE_REBOOT, marker off}. */
purge_config_t purge_config_default(void);

/* Parse "reboot"/"shutdown"/"stay" -> the enum value; -1 for an unknown or NULL string. */
int purge_post_action_from_str(const char *s);

/* The enum as "reboot"/"shutdown"/"stay" ("?" if out of range) — for the config report. */
const char *purge_post_action_str(purge_post_action_t a);

/* Partial update (NULL = leave unchanged). An invalid post_action string returns -1 with
 * *cfg untouched (atomic); else applies the provided fields and returns 0. */
int purge_config_set(purge_config_t *cfg, const char *post_action, const int *marker);

#endif /* PURGE_CONFIG_H */
