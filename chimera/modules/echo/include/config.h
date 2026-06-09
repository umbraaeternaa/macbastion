/* ECHO config core — operator knobs (target rate + burst), validated (§5 §3, EC-1…4). */
#ifndef ECHO_CONFIG_H
#define ECHO_CONFIG_H

#define ECHO_DEFAULT_KBPS 100  /* §3 default bandwidth budget */
#define ECHO_DEFAULT_BURST 200 /* §3 default burst tolerance */
#define ECHO_MIN_KBPS 1
#define ECHO_MAX_KBPS 100000 /* 100 MB/s ceiling — guards against absurd values */
#define ECHO_MIN_BURST 0
#define ECHO_MAX_BURST 100000

typedef struct {
    int target_kbps;
    int burst_tolerance;
} echo_config_t;

/* The §3 defaults: {100, 200}. */
echo_config_t echo_config_default(void);

/* 1 if target_kbps in [MIN,MAX] and burst in [MIN_BURST,MAX_BURST], else 0. */
int echo_config_valid(int target_kbps, int burst);

/* Partial update (mirrors echo.config.set {target_kbps?, burst_tolerance?}): a NULL
 * pointer leaves that field unchanged. Validates every PROVIDED field; on ANY invalid
 * value returns -1 with *cfg untouched (atomic); else applies them and returns 0. */
int echo_config_set(echo_config_t *cfg, const int *target_kbps, const int *burst);

/* Bridge to the shaper: steady bytes-per-tick this config yields at tick_ms. */
long echo_config_budget(echo_config_t cfg, int tick_ms);

#endif /* ECHO_CONFIG_H */
