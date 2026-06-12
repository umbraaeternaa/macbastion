/* C ABI for the CoreBluetooth scanner backend (cb_scanner.mm). Lets the pure-C++
 * CoreBluetoothSource (source.cpp) drive an Objective-C++ CBCentralManager without
 * importing any Apple framework header itself. Manual-tier: needs Bluetooth hardware
 * + the Bluetooth TCC grant. Never fabricates presence (MANIFESTO §4). */
#ifndef TETHER_CB_SCANNER_H
#define TETHER_CB_SCANNER_H

#ifdef __cplusplus
extern "C" {
#endif

typedef struct cb_scanner cb_scanner_t;

/* Begin scanning for a companion advertising `service_uuid`
 * (e.g. "6368696D-6572-6100-0000-000000000001"). Returns NULL if the uuid is empty
 * or malformed; otherwise an opaque handle (scanning starts asynchronously once
 * Bluetooth powers on). */
cb_scanner_t *cb_scanner_start(const char *service_uuid);

/* Snapshot the latest presence. On return *rssi is the last advertised RSSI (dBm)
 * and *seen is 1 iff the companion was heard within the staleness window. Returns 1
 * when the scanner is live (Bluetooth powered on and scanning), 0 when it is not yet
 * ready or was denied — the caller then emits NO presence (never fabricates, §4). */
int cb_scanner_poll(cb_scanner_t *s, double *rssi, int *seen);

/* Stop scanning and release the handle (NULL-safe). */
void cb_scanner_stop(cb_scanner_t *s);

#ifdef __cplusplus
}
#endif

#endif /* TETHER_CB_SCANNER_H */
