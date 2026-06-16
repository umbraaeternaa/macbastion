/* CHAFF Phase-A profile loader (§5.1) — browser-history profile.json -> category weights. */
#include "profile.h"

#include <stdio.h>
#include <stdlib.h>

#include "cJSON.h"

/* CATEGORIES order — mirrors daemon.c's CATEGORIES[] (the canonical Phase-B order). */
static const char *const CATEGORY_NAMES[CHAFF_NUM_CATEGORIES] = {
    "news", "tech", "social", "search", "dev"};

bool chaff_profile_parse(const char *json, double weights_out[CHAFF_NUM_CATEGORIES]) {
    if (!json || !weights_out) {
        return false;
    }
    cJSON *root = cJSON_Parse(json);
    if (!root) {
        return false;
    }
    cJSON *cats = cJSON_GetObjectItemCaseSensitive(root, "categories");
    if (!cJSON_IsObject(cats)) {
        cJSON_Delete(root);
        return false;
    }
    for (size_t i = 0; i < CHAFF_NUM_CATEGORIES; i++) {
        cJSON *w = cJSON_GetObjectItemCaseSensitive(cats, CATEGORY_NAMES[i]);
        weights_out[i] = cJSON_IsNumber(w) ? w->valuedouble : 0.0;
    }
    cJSON_Delete(root);
    return true;
}

bool chaff_profile_load(const char *path, double weights_out[CHAFF_NUM_CATEGORIES]) {
    if (!path || !weights_out) {
        return false;
    }
    FILE *f = fopen(path, "rb");
    if (!f) {
        return false;
    }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (sz <= 0 || sz > (1 << 20)) { /* profile.json is tiny; cap defends against junk */
        fclose(f);
        return false;
    }
    char *buf = malloc((size_t)sz + 1);
    if (!buf) {
        fclose(f);
        return false;
    }
    size_t rd = fread(buf, 1, (size_t)sz, f);
    fclose(f);
    buf[rd] = '\0';
    bool ok = chaff_profile_parse(buf, weights_out);
    free(buf);
    return ok;
}
