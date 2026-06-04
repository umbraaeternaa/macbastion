/* MIRROR — entry point (bootstrap skeleton).
 *
 * The perturbation engine + daemon + IPC land via the TDD RED -> GREEN cycle in
 * subsequent commits. For now main() proves the toolchain: it links and calls
 * into the macOS frameworks MIRROR needs (CoreFoundation + ApplicationServices),
 * using only no-permission APIs (no CGEventTap, no TCC prompt).
 */
#include <ApplicationServices/ApplicationServices.h>
#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
#include <string.h>

#include "mirror.h"

int main(int argc, char **argv) {
    if (argc > 1 && strcmp(argv[1], "--version") == 0) {
        printf("MIRROR %s\n", MIRROR_VERSION);
        return 0;
    }
    printf("MIRROR %s\n", MIRROR_VERSION);
    printf("  CoreFoundation: %.1f\n", (double)kCFCoreFoundationVersionNumber);
    printf("  main display id: %u\n", (unsigned)CGMainDisplayID());
    return 0;
}
