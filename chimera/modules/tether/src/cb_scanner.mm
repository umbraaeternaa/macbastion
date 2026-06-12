/* cb_scanner.mm — the REAL BLE presence backend (TE-real-2, manual-tier). A
 * CBCentralManager scans for the companion's service UUID on a private dispatch
 * queue; each advertisement callback refreshes the latest RSSI + last-seen time.
 * The pure-C++ CoreBluetoothSource (source.cpp) polls a snapshot every tick.
 *
 * No NSRunLoop is needed: a CBCentralManager created with a dispatch queue delivers
 * its delegate callbacks on that queue. Honest empty state (§4): if Bluetooth is
 * off / unauthorized, poll reports not-ready and the daemon emits no presence —
 * it never invents a "present" the radio did not observe. */
#import <CoreBluetooth/CoreBluetooth.h>
#import <Foundation/Foundation.h>

#include "cb_scanner.h"

static const double kStaleSeconds = 4.0; /* heard within 4s == present */

@interface CBScanner : NSObject <CBCentralManagerDelegate>
@property(strong) CBCentralManager *central;
@property(strong) CBUUID *uuid;
@property(assign) double lastRssi;
@property(assign) double lastSeen; /* CFAbsoluteTime; 0 == never heard */
@property(assign) BOOL poweredOn;
@end

@implementation CBScanner
- (instancetype)initWithUUID:(CBUUID *)uuid {
    if ((self = [super init])) {
        _uuid = uuid;
        _lastRssi = 0;
        _lastSeen = 0;
        _poweredOn = NO;
        dispatch_queue_t q =
            dispatch_queue_create("com.umbra.chimera.tether.ble", DISPATCH_QUEUE_SERIAL);
        _central = [[CBCentralManager alloc] initWithDelegate:self queue:q];
    }
    return self;
}

- (void)centralManagerDidUpdateState:(CBCentralManager *)c {
    if (c.state == CBManagerStatePoweredOn) {
        @synchronized(self) {
            self.poweredOn = YES;
        }
        [c scanForPeripheralsWithServices:@[ self.uuid ]
                                  options:@{CBCentralManagerScanOptionAllowDuplicatesKey : @YES}];
    } else {
        @synchronized(self) {
            self.poweredOn = NO;
        }
    }
}

- (void)centralManager:(CBCentralManager *)c
    didDiscoverPeripheral:(CBPeripheral *)p
        advertisementData:(NSDictionary *)adv
                     RSSI:(NSNumber *)rssi {
    (void)c;
    (void)p;
    (void)adv;
    @synchronized(self) {
        self.lastRssi = rssi.doubleValue;
        self.lastSeen = CFAbsoluteTimeGetCurrent();
    }
}
@end

extern "C" cb_scanner_t *cb_scanner_start(const char *service_uuid) {
    if (service_uuid == NULL || service_uuid[0] == '\0') {
        return NULL;
    }
    @autoreleasepool {
        CBUUID *uuid = nil;
        @try {
            uuid = [CBUUID UUIDWithString:[NSString stringWithUTF8String:service_uuid]];
        } @catch (NSException *e) {
            return NULL; /* malformed UUID */
        }
        if (uuid == nil) {
            return NULL;
        }
        CBScanner *scanner = [[CBScanner alloc] initWithUUID:uuid];
        /* Hand a +1 retained, opaque handle to C++; cb_scanner_stop releases it. */
        return (cb_scanner_t *)CFBridgingRetain(scanner);
    }
}

extern "C" int cb_scanner_poll(cb_scanner_t *s, double *rssi, int *seen) {
    if (s == NULL) {
        return 0;
    }
    CBScanner *scanner = (__bridge CBScanner *)s;
    @synchronized(scanner) {
        if (!scanner.poweredOn) {
            return 0; /* not ready / denied — caller emits nothing (§4) */
        }
        double now = CFAbsoluteTimeGetCurrent();
        BOOL heard = (scanner.lastSeen > 0) && ((now - scanner.lastSeen) <= kStaleSeconds);
        if (rssi) {
            *rssi = scanner.lastRssi;
        }
        if (seen) {
            *seen = heard ? 1 : 0;
        }
        return 1;
    }
}

extern "C" void cb_scanner_stop(cb_scanner_t *s) {
    if (s == NULL) {
        return;
    }
    @autoreleasepool {
        CBScanner *scanner = (CBScanner *)CFBridgingRelease(s); /* -1; ARC frees below */
        [scanner.central stopScan];
        scanner.central.delegate = nil;
    }
}
