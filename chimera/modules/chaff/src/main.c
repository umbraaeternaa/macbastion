/* CHAFF daemon entry (§5.1 Phase B).
 *
 * Reads CHIMERA_SOCKET_DIR (default ~/.config/chimera/run) and
 * CHAFF_ENDPOINTS_PATH (default data/endpoints.json), loads the endpoint
 * whitelist, connects OUT to core's command socket, registers, then runs the
 * IPC + generation threads. core.register is fired and the daemon's IPC loop
 * absorbs the ack (classified RESPONSE, ignored).
 */
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cJSON.h"

#include "chaff.h"
#include "commands.h"
#include "daemon.h"
#include "endpoints.h"
#include "http.h"
#include "ipc.h"

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

static char *build_register(void) {
    static const char *const METHODS[] = {
        "chaff.status",         "chaff.profile.start",  "chaff.profile.stop",
        "chaff.generation.start", "chaff.generation.stop", "chaff.config.set",
        "chaff.endpoints.list", "chaff.endpoints.add",
    };
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "jsonrpc", "2.0");
    cJSON_AddNumberToObject(root, "id", 1);
    cJSON_AddStringToObject(root, "method", "core.register");
    cJSON *p = cJSON_CreateObject();
    cJSON_AddStringToObject(p, "module", "chaff");
    cJSON_AddStringToObject(p, "version", CHAFF_VERSION);
    cJSON *methods = cJSON_CreateArray();
    for (size_t i = 0; i < sizeof(METHODS) / sizeof(METHODS[0]); i++) {
        cJSON_AddItemToArray(methods, cJSON_CreateString(METHODS[i]));
    }
    cJSON_AddItemToObject(p, "methods", methods);
    cJSON *events = cJSON_CreateArray();
    cJSON_AddItemToArray(events, cJSON_CreateString("chaff.request.sent"));
    cJSON_AddItemToArray(events, cJSON_CreateString("chaff.error"));
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
        printf("CHAFF %s\n", CHAFF_VERSION);
        return 0;
    }
    signal(SIGPIPE, SIG_IGN);

    const char *ep_path = getenv("CHAFF_ENDPOINTS_PATH");
    if (!ep_path) {
        ep_path = "data/endpoints.json";
    }
    char *json = read_file(ep_path);
    if (!json) {
        fprintf(stderr, "chaff: cannot read endpoints: %s\n", ep_path);
        return 1;
    }
    endpoint_list_t *eps = NULL;
    chaff_result_t pr = endpoints_parse(json, &eps);
    free(json);
    if (pr != CHAFF_OK) {
        fprintf(stderr, "chaff: malformed endpoints json\n");
        return 1;
    }

    char socket_path[1024];
    core_socket_path(socket_path, sizeof(socket_path));

    http_global_init();
    int fd = ipc_connect(socket_path);
    if (fd < 0) {
        fprintf(stderr, "chaff: cannot connect to %s\n", socket_path);
        endpoints_free(eps);
        http_global_cleanup();
        return 1;
    }

    char *reg = build_register();
    if (reg) {
        ipc_send(fd, reg, strlen(reg));
        ipc_send(fd, "\n", 1);
        free(reg);
    }

    chaff_runtime_t rt;
    chaff_runtime_init(&rt);
    int rc = daemon_run(fd, &rt, eps);

    pthread_mutex_destroy(&rt.mutex);
    ipc_close(fd);
    endpoints_free(eps);
    http_global_cleanup();
    return rc;
}
