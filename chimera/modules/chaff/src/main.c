/* CHAFF — entry point (bootstrap skeleton).
 *
 * Phase B (generation) implementation lands via the TDD RED -> GREEN cycle in
 * subsequent commits. For now main() proves the toolchain: it links and calls
 * into every required library and prints their versions.
 */
#include <curl/curl.h>
#include <openssl/opensslv.h>
#include <sqlite3.h>
#include <stdio.h>
#include <string.h>

#include "chaff.h"

int main(int argc, char **argv) {
    if (argc > 1 && strcmp(argv[1], "--version") == 0) {
        printf("CHAFF %s\n", CHAFF_VERSION);
        return 0;
    }
    printf("CHAFF %s\n", CHAFF_VERSION);
    printf("  libcurl: %s\n", curl_version());
    printf("  sqlite3: %s\n", sqlite3_libversion());
    printf("  openssl: %s\n", OPENSSL_VERSION_TEXT);
    return 0;
}
