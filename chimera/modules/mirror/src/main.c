/* MIRROR daemon entry (§5.4 §6).
 *
 * Reads CHIMERA_SOCKET_DIR (default ~/.config/chimera/run) and MIRROR_CONFIG_PATH
 * (default data/config.json), connects OUT to core's command socket, registers,
 * then runs the single inline IPC loop. core.register is fired and the IPC loop
 * absorbs the ack (classified RESPONSE, ignored).
 *
 * Honest scope (MANIFESTO §4): the daemon registers and serves mirror.* via the
 * 4A router, but there is NO real event tap (GATED on code-signing + Accessibility
 * TCC) and NO event producer yet. mirror.enable returns -31004 over the wire.
 */
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cJSON.h"

#include "commands.h"
#include "daemon.h"
#include "exclude.h"
#include "ipc.h"
#include "mirror.h"
#include "profile.h"

static char *read_file(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        return NULL;
    }
    if (fseek(f, 0, SEEK_END) != 0) {
        fclose(f);
        return NULL;
    }
    long size = ftell(f);
    if (size < 0) {
        fclose(f);
        return NULL;
    }
    rewind(f);
    char *buf = malloc((size_t)size + 1);
    if (!buf) {
        fclose(f);
        return NULL;
    }
    size_t got = fread(buf, 1, (size_t)size, f);
    fclose(f);
    buf[got] = '\0';
    return buf;
}

/* Apply config.json over the already-initialised runtime defaults (non-fatal:
 * a missing or malformed file leaves the runtime_init defaults intact). */
static void apply_config(mirror_runtime_t *rt, const char *path) {
    char *json = read_file(path);
    if (!json) {
        fprintf(stderr, "mirror: no config at %s — using defaults (medium, no exclusions)\n", path);
        return;
    }
    cJSON *root = cJSON_Parse(json);
    free(json);
    if (!root) {
        fprintf(stderr, "mirror: malformed config %s — using defaults\n", path);
        return;
    }
    cJSON *prof = cJSON_GetObjectItemCaseSensitive(root, "profile");
    if (cJSON_IsString(prof)) {
        mirror_profile_t p = profile_from_str(prof->valuestring);
        if (p != (mirror_profile_t)(-1)) {
            rt->profile = p;
        } else {
            fprintf(stderr, "mirror: unknown profile '%s' — keeping default\n", prof->valuestring);
        }
    }
    cJSON *excl = cJSON_GetObjectItemCaseSensitive(root, "exclusions");
    if (cJSON_IsArray(excl)) {
        cJSON *item = NULL;
        cJSON_ArrayForEach(item, excl) {
            if (cJSON_IsString(item)) {
                exclude_add(&rt->exclusions, item->valuestring);
            }
        }
    }
    cJSON_Delete(root);
}

static char *build_register(void) {
    static const char *const METHODS[] = {
        "mirror.status",         "mirror.enable",         "mirror.disable",
        "mirror.profile.set",    "mirror.exclude.add",    "mirror.exclude.remove",
        "mirror.exclude.list",   "mirror.stats",
    };
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "jsonrpc", "2.0");
    cJSON_AddNumberToObject(root, "id", 1);
    cJSON_AddStringToObject(root, "method", "core.register");
    cJSON *p = cJSON_CreateObject();
    cJSON_AddStringToObject(p, "module", "mirror");
    cJSON_AddStringToObject(p, "version", MIRROR_VERSION);
    cJSON *methods = cJSON_CreateArray();
    for (size_t i = 0; i < sizeof(METHODS) / sizeof(METHODS[0]); i++) {
        cJSON_AddItemToArray(methods, cJSON_CreateString(METHODS[i]));
    }
    cJSON_AddItemToObject(p, "methods", methods);
    /* Only events MIRROR can actually emit today. permission.lost / tap.disabled
     * are registered when the GATED event tap lands. */
    cJSON *events = cJSON_CreateArray();
    cJSON_AddItemToArray(events, cJSON_CreateString("mirror.profile.changed"));
    cJSON_AddItemToArray(events, cJSON_CreateString("mirror.error"));
    cJSON_AddItemToObject(p, "events", events);
    cJSON_AddItemToObject(p, "depends_on", cJSON_CreateArray());
    cJSON_AddItemToObject(root, "params", p);
    char *s = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    return s;
}

static void core_socket_path(char *out, size_t outsz) {
    const char *dir = getenv("CHIMERA_SOCKET_DIR");
    if (dir) {
        snprintf(out, outsz, "%s/core.sock", dir);
    } else {
        const char *home = getenv("HOME");
        snprintf(out, outsz, "%s/.config/chimera/run/core.sock", home ? home : ".");
    }
}

int main(int argc, char **argv) {
    if (argc > 1 && strcmp(argv[1], "--version") == 0) {
        printf("MIRROR %s\n", MIRROR_VERSION);
        return 0;
    }
    signal(SIGPIPE, SIG_IGN);

    const char *cfg_path = getenv("MIRROR_CONFIG_PATH");
    if (!cfg_path) {
        cfg_path = "data/config.json";
    }

    /* Defaults first, then config on top — config overrides, never the reverse. */
    mirror_runtime_t rt;
    mirror_runtime_init(&rt);
    apply_config(&rt, cfg_path);

    char socket_path[1024];
    core_socket_path(socket_path, sizeof(socket_path));

    int fd = ipc_connect(socket_path);
    if (fd < 0) {
        fprintf(stderr, "mirror: cannot connect to %s\n", socket_path);
        pthread_mutex_destroy(&rt.mutex);
        return 1;
    }

    char *reg = build_register();
    if (reg) {
        ipc_send(fd, reg, strlen(reg));
        ipc_send(fd, "\n", 1);
        free(reg);
    }

    int rc = daemon_run(fd, &rt);

    pthread_mutex_destroy(&rt.mutex);
    ipc_close(fd);
    return rc;
}
