/* ECHO daemon entry — RED bootstrap (EL-6). Exits immediately; it never connects or
 * registers, so the integration test fails until the socket loop (ipc/daemon/main) lands
 * in GREEN. An honest stub (MANIFESTO §4). */
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc > 1 && strcmp(argv[1], "--version") == 0) {
        printf("ECHO bootstrap\n");
    }
    return 0;
}
