/* PURGE daemon entry — RED bootstrap (PL-6). Exits immediately; never connects or
 * registers, so the integration test fails until the socket loop (ipc/daemon/main) lands
 * in GREEN. An honest stub (MANIFESTO §4). */
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc > 1 && strcmp(argv[1], "--version") == 0) {
        printf("PURGE bootstrap\n");
    }
    return 0;
}
