/* commands — mirror.* JSON-RPC dispatch (§5.4 §5). status, profile.set, the
 * exclude add/remove/list ops, stats and disable operate on the in-memory
 * runtime; enable is GATED (-31004) until code-signing + Accessibility TCC exist
 * (§6/§9, Sub-M1). */
#include "commands.h"

#include <ApplicationServices/ApplicationServices.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include "jsonrpc.h"
#include "perturb.h"

/* Accessibility-permission probe (AX-1). Real default asks the OS via the public TCC
 * API; tests inject a deterministic stub through mirror_set_accessibility_check. */
static int mirror_ax_trusted_real(void) { return AXIsProcessTrusted() ? 1 : 0; }
static int (*g_ax_check)(void) = mirror_ax_trusted_real;

void mirror_set_accessibility_check(int (*fn)(void)) {
    g_ax_check = fn ? fn : mirror_ax_trusted_real;
}

/* Input injector (AX-2). Real backend = the CGEvent posting loop (GREEN step; manual-tier).
 * Returns 0 on success, nonzero on failure. */
static int mirror_injector_start_real(mirror_runtime_t *rt);
static int (*g_injector_start)(mirror_runtime_t *) = mirror_injector_start_real;

void mirror_set_injector(int (*start)(mirror_runtime_t *rt)) {
    g_injector_start = start ? start : mirror_injector_start_real;
}

/* Secure-field probe (AX-3) — declared before the injector loop, which consults it each
 * tick to downgrade to "light" on password fields. Real backend + setter below. */
static int mirror_secure_field_real(void);
static int (*g_secure_field_check)(void) = mirror_secure_field_real;

/* Real injector (manual-tier — needs a live Accessibility grant; not exercised by the
 * unit suite, which injects a stub). While enabled, post small humanlike mouse-move
 * perturbations: read the cursor, add a Gaussian delta (perturb_mouse) scaled by the
 * active profile, and CGEventPost it; sleep a jittered gap (perturb_timing) between
 * events. Stops when rt->enabled is cleared (mirror.disable). */
static void *mirror_injector_loop(void *arg) {
    mirror_runtime_t *rt = (mirror_runtime_t *)arg;
    CGEventSourceRef src = CGEventSourceCreate(kCGEventSourceStateHIDSystemState);
    for (;;) {
        int secure = g_secure_field_check(); /* OS query — outside the lock */
        pthread_mutex_lock(&rt->mutex);
        int on = rt->enabled;
        mirror_profile_params_t pp = mirror_tick_params(rt, secure); /* light on secure fields */
        double dx = 0.0, dy = 0.0;
        perturb_mouse(&dx, &dy, pp.mouse_sigma, &rt->rng_state);
        int gap = perturb_timing(40, pp.flight_delta, &rt->rng_state);
        pthread_mutex_unlock(&rt->mutex);
        if (!on) {
            break;
        }
        CGEventRef probe = CGEventCreate(NULL);
        CGPoint p = probe ? CGEventGetLocation(probe) : CGPointMake(0, 0);
        if (probe) {
            CFRelease(probe);
        }
        CGEventRef mv = CGEventCreateMouseEvent(src, kCGEventMouseMoved,
                                                CGPointMake(p.x + dx, p.y + dy),
                                                kCGMouseButtonLeft);
        if (mv) {
            CGEventPost(kCGHIDEventTap, mv);
            CFRelease(mv);
        }
        usleep((useconds_t)(gap < 10 ? 10 : gap) * 1000);
    }
    if (src) {
        CFRelease(src);
    }
    return NULL;
}

static int mirror_injector_start_real(mirror_runtime_t *rt) {
    if (!rt) {
        return -1;
    }
    pthread_t t;
    if (pthread_create(&t, NULL, mirror_injector_loop, rt) != 0) {
        return -1;
    }
    pthread_detach(t);
    return 0;
}

void mirror_set_secure_field_check(int (*fn)(void)) {
    g_secure_field_check = fn ? fn : mirror_secure_field_real;
}

/* Real secure-field probe (AX-3; manual-tier — needs Accessibility). Inspects the
 * system-wide focused UI element's subrole; nonzero iff it is a secure text field. */
static int mirror_secure_field_real(void) {
    AXUIElementRef sys = AXUIElementCreateSystemWide();
    if (!sys) {
        return 0;
    }
    CFTypeRef focused = NULL;
    int secure = 0;
    if (AXUIElementCopyAttributeValue(sys, kAXFocusedUIElementAttribute, &focused) ==
            kAXErrorSuccess &&
        focused) {
        CFTypeRef sub = NULL;
        if (AXUIElementCopyAttributeValue((AXUIElementRef)focused, kAXSubroleAttribute,
                                          &sub) == kAXErrorSuccess &&
            sub) {
            if (CFGetTypeID(sub) == CFStringGetTypeID() &&
                CFStringCompare((CFStringRef)sub, CFSTR("AXSecureTextField"), 0) ==
                    kCFCompareEqualTo) {
                secure = 1;
            }
            CFRelease(sub);
        }
        CFRelease(focused);
    }
    CFRelease(sys);
    return secure;
}

mirror_profile_params_t mirror_tick_params(const mirror_runtime_t *rt, int is_secure_field) {
    mirror_profile_t base = rt ? rt->profile : MIRROR_PROFILE_DEFAULT;
    return profile_params(profile_downgrade(base, is_secure_field != 0));
}

void mirror_runtime_init(mirror_runtime_t *rt) {
    if (!rt) {
        return;
    }
    rt->enabled = 0;
    rt->profile = MIRROR_PROFILE_DEFAULT; /* medium (§3) */
    rt->exclusions.count = 0;
    for (int i = 0; i < MIRROR_EV__COUNT; i++) {
        rt->stats.counts[i] = 0;
    }
    rt->rng_state = (uint64_t)time(NULL) ^ 0x9e3779b97f4a7c15ULL; /* nonzero seed */
    pthread_mutex_init(&rt->mutex, NULL);
    rt->stop = 0;
    rt->evq_head = NULL;
    rt->evq_tail = NULL;
    rt->heartbeat_at = 0;
    inputagg_reset(&rt->input);
    rt->input_minute_at = 0; /* armed on the first tick */
}

/* {"ok": true} success body. */
static char *ok_result(const cJSON *id) {
    cJSON *r = cJSON_CreateObject();
    cJSON_AddBoolToObject(r, "ok", 1);
    return jsonrpc_serialize_response(id, r);
}

/* {"exclusions": [...]} from the runtime list. */
static char *exclusions_result(const mirror_runtime_t *rt, const cJSON *id) {
    cJSON *r = cJSON_CreateObject();
    cJSON *arr = cJSON_CreateArray();
    if (rt) {
        for (size_t i = 0; i < rt->exclusions.count; i++) {
            cJSON_AddItemToArray(arr, cJSON_CreateString(rt->exclusions.items[i]));
        }
    }
    cJSON_AddItemToObject(r, "exclusions", arr);
    return jsonrpc_serialize_response(id, r);
}

char *commands_dispatch(mirror_runtime_t *rt, const char *method, const cJSON *params,
                        const cJSON *id) {
    if (!method) {
        return NULL;
    }

    if (strcmp(method, "mirror.status") == 0) {
        uint64_t shaped = 0;
        if (rt) {
            for (int i = 0; i < MIRROR_EV__COUNT; i++) {
                shaped += rt->stats.counts[i];
            }
        }
        cJSON *r = cJSON_CreateObject();
        cJSON_AddBoolToObject(r, "enabled", rt && rt->enabled);
        cJSON_AddStringToObject(r, "profile",
                                profile_to_str(rt ? rt->profile : MIRROR_PROFILE_DEFAULT));
        cJSON_AddNumberToObject(r, "events_shaped_today", (double)shaped);
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "mirror.profile.set") == 0) {
        cJSON *p = cJSON_GetObjectItemCaseSensitive(params, "profile");
        if (!rt || !cJSON_IsString(p)) {
            return jsonrpc_serialize_error(id, -32602, "invalid params: profile required", NULL);
        }
        mirror_profile_t prof = profile_from_str(p->valuestring);
        if (prof == (mirror_profile_t)(-1)) {
            return jsonrpc_serialize_error(id, -32602, "invalid params: unknown profile", NULL);
        }
        rt->profile = prof;
        cJSON *r = cJSON_CreateObject();
        cJSON_AddStringToObject(r, "profile", profile_to_str(rt->profile));
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "mirror.exclude.add") == 0 ||
        strcmp(method, "mirror.exclude.remove") == 0) {
        cJSON *b = cJSON_GetObjectItemCaseSensitive(params, "bundle_id");
        if (!rt || !cJSON_IsString(b)) {
            return jsonrpc_serialize_error(id, -32602, "invalid params: bundle_id required", NULL);
        }
        mirror_result_t rc = (method[15] == 'a') /* "mirror.exclude.[a]dd" vs "[r]emove" */
                                 ? exclude_add(&rt->exclusions, b->valuestring)
                                 : exclude_remove(&rt->exclusions, b->valuestring);
        if (rc != MIRROR_OK) {
            return jsonrpc_serialize_error(id, MIRROR_RPC_PRECONDITION_FAILED,
                                           "exclusion list full or entry not found", NULL);
        }
        return exclusions_result(rt, id);
    }

    if (strcmp(method, "mirror.exclude.list") == 0) {
        return exclusions_result(rt, id);
    }

    if (strcmp(method, "mirror.stats") == 0) {
        static const char *const NAMES[MIRROR_EV__COUNT] = {"mouse_move", "mouse_click", "key_down",
                                                            "key_up", "scroll"};
        cJSON *r = cJSON_CreateObject();
        for (int i = 0; i < MIRROR_EV__COUNT; i++) {
            cJSON_AddNumberToObject(r, NAMES[i], rt ? (double)rt->stats.counts[i] : 0.0);
        }
        return jsonrpc_serialize_response(id, r);
    }

    if (strcmp(method, "mirror.disable") == 0) {
        if (rt) {
            rt->enabled = 0;
        }
        return ok_result(id);
    }

    if (strcmp(method, "mirror.enable") == 0) {
        /* AX-1/AX-2: consult the REAL Accessibility permission. Not granted -> honest,
         * actionable error. Granted -> start the input injector and go live. */
        if (!g_ax_check()) {
            cJSON *data = cJSON_CreateObject();
            cJSON_AddStringToObject(data, "spec", "\xc2\xa7""6/\xc2\xa7""9");
            cJSON_AddBoolToObject(data, "accessibility_granted", 0);
            cJSON_AddStringToObject(data, "required_capability", "accessibility");
            return jsonrpc_serialize_error(
                id, MIRROR_RPC_PRECONDITION_FAILED,
                "mirror.enable requires Accessibility permission (grant it in System "
                "Settings > Privacy & Security > Accessibility)",
                data);
        }
        /* Accessibility granted: mark enabled, then start the injector (it reads
         * rt->enabled, so set it first — dispatch holds the runtime mutex throughout, so
         * the injector thread can't observe a half-state). Roll back if it fails to start. */
        if (rt) {
            rt->enabled = 1;
        }
        if (rt && g_injector_start(rt) == 0) {
            return ok_result(id);
        }
        if (rt) {
            rt->enabled = 0;
        }
        cJSON *data = cJSON_CreateObject();
        cJSON_AddBoolToObject(data, "accessibility_granted", 1);
        cJSON_AddStringToObject(data, "required_capability", "injector");
        return jsonrpc_serialize_error(
            id, MIRROR_RPC_PRECONDITION_FAILED,
            "mirror.enable: Accessibility granted but the input injector failed to start",
            data);
    }

    return jsonrpc_serialize_error(id, -32601, "method not found", NULL);
}

/* Enqueue an owned NDJSON line on the runtime's event queue (caller holds rt->mutex). */
static void evq_push(mirror_runtime_t *rt, char *line) {
    mirror_event_node_t *node = calloc(1, sizeof(*node));
    if (!node) {
        free(line);
        return;
    }
    node->line = line;
    node->next = NULL;
    if (rt->evq_tail) {
        rt->evq_tail->next = node;
    } else {
        rt->evq_head = node;
    }
    rt->evq_tail = node;
}

void mirror_emit_input_minute(mirror_runtime_t *rt, const mirror_inputagg_t *snap) {
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "jsonrpc", "2.0");
    cJSON_AddStringToObject(root, "method", "mirror.input.minute");
    cJSON *params = cJSON_CreateObject();
    cJSON_AddNumberToObject(params, "chars", (double)snap->chars);
    cJSON_AddNumberToObject(params, "deletes", (double)snap->deletes);
    double ratio = inputagg_mouse_ratio(snap);
    if (ratio > 0.0) {
        cJSON_AddNumberToObject(params, "mouse_path_ratio", ratio);
    } else {
        cJSON_AddNullToObject(params, "mouse_path_ratio"); /* no movement -> absent */
    }
    cJSON_AddItemToObject(root, "params", params);
    char *line = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    if (line) {
        evq_push(rt, line);
    }
}

int mirror_tick_input_minute(mirror_runtime_t *rt, time_t now) {
    if (rt->input_minute_at == 0) {
        rt->input_minute_at = now; /* arm the first window — no emit yet */
        return 0;
    }
    if (now - rt->input_minute_at < MIRROR_INPUT_MINUTE_S) {
        return 0;
    }
    mirror_inputagg_t snap;
    inputagg_roll(&rt->input, &snap); /* snapshot the minute + reset the live window */
    mirror_emit_input_minute(rt, &snap);
    rt->input_minute_at = now;
    return 1;
}

int mirror_keycode_is_delete(int keycode) {
    return keycode == 51 || keycode == 117; /* kVK_Delete / kVK_ForwardDelete */
}

void mirror_observe_event(mirror_runtime_t *rt, int kind, int keycode, double dx, double dy) {
    if (kind == MIRROR_INPUT_KEY) {
        inputagg_key(&rt->input, mirror_keycode_is_delete(keycode));
    } else if (kind == MIRROR_INPUT_MOUSE) {
        inputagg_mouse_move(&rt->input, dx, dy);
    }
}
