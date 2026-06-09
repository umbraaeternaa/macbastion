/* ECHO daemon entry (§5.2 / §6). Reads CHIMERA_SOCKET_DIR (default ~/.config/chimera/run),
 * connects OUT to core's command socket, registers, then runs the IPC serve loop. The
 * core.register ack is absorbed by the loop (classified RESPONSE, ignored). */
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cJSON.h"

#include "commands.h"
#include "daemon.h"
#include "ipc.h"

#define ECHO_VERSION "0.1.0-alpha"

static char *build_register(void) {
    static const char *const METHODS[] = {
        "echo.status", "echo.start",      "echo.stop",
        "echo.config.set", "echo.config.get", "echo.stats",
    };
    static const char *const EVENTS[] = {
        "echo.rate.violation",
        "echo.padding.surge",
        "echo.error",
    };
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "jsonrpc", "2.0");
    cJSON_AddNumberToObject(root, "id", 1);
    cJSON_AddStringToObject(root, "method", "core.register");
    cJSON *p = cJSON_CreateObject();
    cJSON_AddStringToObject(p, "module", "echo");
    cJSON_AddStringToObject(p, "version", ECHO_VERSION);
    cJSON *methods = cJSON_CreateArray();
    for (size_t i = 0; i < sizeof(METHODS) / sizeof(METHODS[0]); i++) {
        cJSON_AddItemToArray(methods, cJSON_CreateString(METHODS[i]));
    }
    cJSON_AddItemToObject(p, "methods", methods);
    cJSON *events = cJSON_CreateArray();
    for (size_t i = 0; i < sizeof(EVENTS) / sizeof(EVENTS[0]); i++) {
        cJSON_AddItemToArray(events, cJSON_CreateString(EVENTS[i]));
    }
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
        printf("ECHO %s\n", ECHO_VERSION);
        return 0;
    }
    signal(SIGPIPE, SIG_IGN);

    char socket_path[1024];
    core_socket_path(socket_path, sizeof(socket_path));
    int fd = ipc_connect(socket_path);
    if (fd < 0) {
        fprintf(stderr, "echo: cannot connect to %s\n", socket_path);
        return 1;
    }

    char *reg = build_register();
    if (reg) {
        ipc_send(fd, reg, strlen(reg));
        ipc_send(fd, "\n", 1);
        free(reg);
    }

    echo_runtime_t rt;
    echo_runtime_init(&rt);
    int rc = echo_daemon_run(fd, &rt);

    ipc_close(fd);
    return rc;
}
