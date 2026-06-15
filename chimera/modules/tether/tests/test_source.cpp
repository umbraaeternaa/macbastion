/* TE-real: companion-identity matcher (pure). The real BLE/Classic source is
 * manual-tier (hardware + TCC); THIS is the hermetic, testable core every backend
 * needs — "is this discovered device my configured companion?". */
#include <cstdio>
#include <fstream>
#include <string>

#include "unity.h"

#include "source.hpp"
#include "tests.hpp"

using tether::companion_matches;
using tether::normalize_bt_addr;

/* normalize: strip separators (':' '-'), lowercase — so formatting never matters. */
static void test_normalize_lowercases_and_strips_separators(void) {
    TEST_ASSERT_EQUAL_STRING("a8798d901c83", normalize_bt_addr("A8:79:8D:90:1C:83").c_str());
    TEST_ASSERT_EQUAL_STRING("a8798d901c83", normalize_bt_addr("a8-79-8d-90-1c-83").c_str());
    TEST_ASSERT_EQUAL_STRING("a8798d901c83", normalize_bt_addr("A8798D901C83").c_str());
}

/* The Samsung S22 matches itself across any formatting. */
static void test_companion_matches_case_and_separator_insensitive(void) {
    TEST_ASSERT_TRUE(companion_matches("A8:79:8D:90:1C:83", "a8:79:8d:90:1c:83"));
    TEST_ASSERT_TRUE(companion_matches("A8:79:8D:90:1C:83", "A8798D901C83"));
    TEST_ASSERT_TRUE(companion_matches("a8-79-8d-90-1c-83", "A8:79:8D:90:1C:83"));
}

/* A different paired device (the stray iPhone) is NOT the companion. */
static void test_companion_no_match_different_device(void) {
    TEST_ASSERT_FALSE(companion_matches("A8:79:8D:90:1C:83", "18:E7:B0:77:30:B3"));
}

/* No companion configured → never claim presence (honest empty state, §4). */
static void test_companion_empty_config_never_matches(void) {
    TEST_ASSERT_FALSE(companion_matches("", "A8:79:8D:90:1C:83"));
    TEST_ASSERT_FALSE(companion_matches("A8:79:8D:90:1C:83", ""));
}

/* Source-sharing wiring: the live BLE source must BORROW the runtime's CompanionPin
 * (one shared object), not own a private copy — otherwise tether.unpair clears a
 * different pin and never bites the running scanner. We prove the sharing on BOTH
 * mutations: pinning via the shared handle is seen by the source, and an external
 * unpair() resets what the source sees. A private copy would fail the unpair assert.
 * Hermetic: an empty companion_id keeps the scanner unstarted (no Bluetooth/TCC). */
static void test_source_borrows_shared_pin(void) {
    tether::CompanionPin pin;
    tether::CoreBluetoothSource src("", pin); /* shares the runtime's pin (no hardware) */
    pin.accept("A8:79:8D:90:1C:83");          /* pin the companion via the SHARED handle */
    TEST_ASSERT_TRUE(src.pinned());           /* the source sees it -> shared, not a copy */
    pin.unpair();                             /* tether.unpair fires on the same object */
    TEST_ASSERT_FALSE(src.pinned());          /* ...and the source's view resets -> bites live */
}

/* LiveFileSource (TE-bridge): reads presence from an external scanner's feed file. The last
 * line drives the sample — "PRESENT  rssi= N" -> seen + that rssi; "absent" -> not seen. Lets
 * the dead-man ride a Bluetooth-authorized helper (ble-probe) when tether is TCC-denied. */
static void test_live_file_source_parses_feed(void) {
    const char *path = "/tmp/chimera_lfs_test.feed";
    {
        std::ofstream f(path);
        f << "[t+ 1s] PRESENT  rssi= -55 dBm  (companion heard <4s ago)\n";
    }
    tether::LiveFileSource src(path);
    tether::Sample s{};
    TEST_ASSERT_TRUE(src.next(s));
    TEST_ASSERT_TRUE(s.seen);
    TEST_ASSERT_TRUE(s.rssi < -50.0 && s.rssi > -60.0); /* parsed ~-55 */
    {
        std::ofstream f(path);
        f << "[t+ 2s] absent   (our UUID not heard in the last 4s)\n";
    }
    TEST_ASSERT_TRUE(src.next(s));
    TEST_ASSERT_FALSE(s.seen); /* absent line -> not seen */
    std::remove(path);
}

void run_source_tests(void) {
    RUN_TEST(test_normalize_lowercases_and_strips_separators);
    RUN_TEST(test_companion_matches_case_and_separator_insensitive);
    RUN_TEST(test_companion_no_match_different_device);
    RUN_TEST(test_companion_empty_config_never_matches);
    RUN_TEST(test_source_borrows_shared_pin);
    RUN_TEST(test_live_file_source_parses_feed);
}
