/* companion_beacon — a reliable CHIMERA dead-man companion (the mirror of cb_scanner.mm).
 *
 * A CBPeripheralManager advertises the agreed BLE service UUID so TETHER's scanner sees a
 * STABLE presence (no flaky third-party advertiser). Run it on the device you carry — a spare
 * Mac / iPad / an iPhone via Xcode; when it leaves range, TETHER's dead-man fires. By default it
 * advertises the project UUID 6368696D-6572-6100-0000-000000000001 ("chimera" in ASCII), the
 * same default TETHER watches — so the demo is turnkey: run this, set companion_id to that UUID.
 *
 * Manual-tier (real CoreBluetooth, exactly like the scanner): not unit-testable; verified by
 * running it and watching `tether.status` (rssi_smoothed > 0, state NEAR). Needs the Bluetooth
 * grant — the embedded __info_plist (NSBluetoothAlwaysUsageDescription) makes macOS prompt with a
 * reason on first run. Runs until Ctrl-C.
 *
 *   companion-beacon [service-uuid] [local-name]
 */
#import <CoreBluetooth/CoreBluetooth.h>
#import <Foundation/Foundation.h>

#include <cstdio>

static const char *kDefaultUUID = "6368696D-6572-6100-0000-000000000001"; /* "chimera" */
static const char *kDefaultName = "CHIMERA-companion";

@interface Beacon : NSObject <CBPeripheralManagerDelegate>
@property(strong) CBPeripheralManager *pm;
@property(strong) CBUUID *uuid;
@property(strong) NSString *localName;
@end

@implementation Beacon
- (instancetype)initWithUUID:(CBUUID *)uuid name:(NSString *)name {
    if ((self = [super init])) {
        _uuid = uuid;
        _localName = name;
        /* queue:nil -> delegate callbacks on the main queue; main() runs the run loop. */
        _pm = [[CBPeripheralManager alloc] initWithDelegate:self queue:nil];
    }
    return self;
}

- (void)peripheralManagerDidUpdateState:(CBPeripheralManager *)pm {
    if (pm.state == CBManagerStatePoweredOn) {
        [pm startAdvertising:@{
            CBAdvertisementDataServiceUUIDsKey : @[ self.uuid ],
            CBAdvertisementDataLocalNameKey : self.localName,
        }];
        fprintf(stderr,
                "[companion-beacon] advertising service %s as \"%s\" — carry this device; "
                "Ctrl-C to stop.\n",
                self.uuid.UUIDString.UTF8String, self.localName.UTF8String);
    } else {
        /* Honest empty state (§4): no advertising unless the radio is actually on + authorized. */
        fprintf(stderr,
                "[companion-beacon] Bluetooth not ready (state %ld) — turn Bluetooth on / grant "
                "the permission, then re-run.\n",
                (long)pm.state);
    }
}
@end

int main(int argc, const char **argv) {
    @autoreleasepool {
        const char *uuidStr = (argc > 1) ? argv[1] : kDefaultUUID;
        const char *nameStr = (argc > 2) ? argv[2] : kDefaultName;
        CBUUID *uuid = nil;
        @try {
            uuid = [CBUUID UUIDWithString:[NSString stringWithUTF8String:uuidStr]];
        } @catch (NSException *e) {
            fprintf(stderr, "[companion-beacon] malformed service UUID: %s\n", uuidStr);
            return 2;
        }
        Beacon *beacon = [[Beacon alloc] initWithUUID:uuid
                                                 name:[NSString stringWithUTF8String:nameStr]];
        (void)beacon; /* retained by the run loop's delegate reference */
        [[NSRunLoop currentRunLoop] run]; /* advertise until the process is killed */
    }
    return 0;
}
