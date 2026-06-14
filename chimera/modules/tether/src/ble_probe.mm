/* ble_probe — a standalone CHIMERA TETHER presence probe (dev/demo, manual-tier).
 *
 * The durable re-build of the throwaway /tmp/probe_src we lost: it drives our REAL
 * cb_scanner (cb_scanner.mm) against a BLE service UUID and prints live RSSI + seen
 * status once a second. Use it to PROVE the Mac sees the companion — e.g. a Samsung
 * running nRF Connect advertising our UUID — BEFORE wiring the full dead-man. No core,
 * no organism: it isolates just the BLE link.
 *
 * Needs the Bluetooth grant — the embedded __info_plist (NSBluetoothAlwaysUsageDescription)
 * makes macOS prompt with a reason on first run. Runs until Ctrl-C.
 *
 *   ble-probe [service-uuid]    (default: the project UUID 6368696D-…-0001)
 */
#import <Foundation/Foundation.h>

#include <cstdio>
#include <unistd.h>

#include "cb_scanner.h"

static const char *kDefaultUUID = "6368696D-6572-6100-0000-000000000001"; /* "chimera" */

int main(int argc, const char **argv) {
    const char *uuid = (argc > 1) ? argv[1] : kDefaultUUID;
    cb_scanner_t *sc = cb_scanner_start(uuid);
    if (sc == NULL) {
        std::fprintf(stderr, "[ble-probe] could not start scanner (malformed UUID?): %s\n", uuid);
        return 2;
    }
    std::fprintf(stderr, "[ble-probe] scanning for service %s — Ctrl-C to stop.\n", uuid);
    for (int tick = 0;; ++tick) {
        double rssi = 0;
        int seen = 0;
        int ready = cb_scanner_poll(sc, &rssi, &seen);
        if (!ready) {
            std::fprintf(stderr,
                         "[t+%4ds] Bluetooth NOT READY / unauthorized — turn BT on + grant the "
                         "permission, then it starts.\n",
                         tick);
        } else if (seen) {
            std::fprintf(stderr, "[t+%4ds] PRESENT  rssi=%4.0f dBm  (companion heard <4s ago)\n",
                         tick, rssi);
        } else {
            std::fprintf(stderr, "[t+%4ds] absent   (our UUID not heard in the last 4s)\n", tick);
        }
        sleep(1);
    }
    /* not reached — Ctrl-C terminates the process; the OS reclaims the scanner. */
}
