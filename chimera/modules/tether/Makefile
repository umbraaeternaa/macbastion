# CHIMERA TETHER — Proximity Dead-Man Switch (§5.7). The ONLY C++ module.
#   make         build the tether daemon binary
#   make test    build + run the Unity test suite (C++ engine, extern "C" setUp)
#   make format  clang-format our sources (vendored excluded)
#   make clean   remove build artifacts
#
# Slice 1: presence/classify/escalation ENGINE (pure logic, hermetic) + event
# emission + tether.* command dispatch. BLE source (CoreBluetooth .mm) and IRK
# pairing (Keychain/Secure Enclave) are GATED. Escalation is EMIT-ONLY — core
# enforces L1/L2/L3 (spec §5). No real lock/evict/reboot here.
#
# Mixed toolchain: our logic is C++17 (clang++); vendored cJSON + the shared
# modules/common jsonrpc.c are C (clang); Unity is C. Link with clang++.
CXX := clang++
CC  := clang

# -I../common: the shared jsonrpc (JE-1 extract; no longer a per-module copy).
INCLUDES  := -Iinclude -Isrc/vendor/cjson -I../common
CXXSTRICT := -std=c++17 -Wall -Wextra -Werror -O2 $(INCLUDES)
CSTRICT   := -std=c17 -Wall -Wextra -Werror -O2 $(INCLUDES)
CRELAXED  := -std=c17 -O2 $(INCLUDES)
TESTINC   := -Itests/vendor/unity -DUNITY_INCLUDE_DOUBLE
TESTCXX   := -std=c++17 -Wall -Wextra -O2 $(INCLUDES) $(TESTINC)
# Objective-C++ (the real BLE scanner, cb_scanner.mm) — ARC; relaxed like vendored
# glue (Apple framework headers aren't -Werror-clean). Links CoreBluetooth+Foundation.
MMSTRICT  := -std=c++17 -Wall -Wextra -O2 -fobjc-arc $(INCLUDES)
FRAMEWORKS := -framework Foundation -framework CoreBluetooth

BIN       := tether
CPP_OBJS  := $(patsubst %.cpp,%.o,$(filter-out src/main.cpp,$(wildcard src/*.cpp)))
MM_OBJS   := src/cb_scanner.o               # Objective-C++ BLE backend (TE-real-2)
C_OBJS    := ../common/jsonrpc.o           # shared jsonrpc (JE-1 extract; ends TE-7b, was the 4th copy)
VEND_OBJS := src/vendor/cjson/cJSON.o
UNITY_OBJ := tests/vendor/unity/unity.o
TEST_OBJS := $(patsubst %.cpp,%.o,$(wildcard tests/*.cpp))

$(BIN): src/main.o $(CPP_OBJS) $(MM_OBJS) $(C_OBJS) $(VEND_OBJS) src/tether.plist
	$(CXX) $(filter-out src/tether.plist,$^) $(FRAMEWORKS) \
	  -Wl,-sectcreate,__TEXT,__info_plist,src/tether.plist -o $@

# app — wrap the daemon binary in a proper .app bundle (OPEN TAIL #1 root fix). A bare signed
# Mach-O launched by a LaunchAgent is TCC-attributed by absolute path (client_type=1) and the
# Bluetooth grant never binds to the daemon; a real bundle (CFBundleIdentifier + Info.plist,
# signed AS the bundle) gives macOS a stable bundle-id + designated requirement, so TCC binds
# the grant to the daemon and it persists across rebuilds + reboot. Signing is a separate step
# (../../sign.sh / codesign, which needs the operator's identity) — this target only assembles.
TETHER_APP := tether.app
app: $(BIN) src/tether.Info.plist
	rm -rf $(TETHER_APP)
	mkdir -p $(TETHER_APP)/Contents/MacOS
	cp $(BIN) $(TETHER_APP)/Contents/MacOS/tether
	cp src/tether.Info.plist $(TETHER_APP)/Contents/Info.plist

# companion-beacon — a standalone CoreBluetooth advertiser: the turnkey/demo dead-man companion
# (the mirror of cb_scanner.mm). Manual-tier like the scanner. The embedded __info_plist carries
# NSBluetoothAlwaysUsageDescription so macOS prompts for the Bluetooth grant with a reason.
companion: src/companion_beacon.mm src/companion_beacon.plist
	$(CXX) $(MMSTRICT) src/companion_beacon.mm $(FRAMEWORKS) \
	  -Wl,-sectcreate,__TEXT,__info_plist,src/companion_beacon.plist -o companion-beacon

# ble-probe — a standalone scanner over our real cb_scanner: prints live RSSI/seen for a
# service UUID. Durable re-build of the lost /tmp probe; proves the Mac sees the companion
# (e.g. a Samsung running nRF Connect on our UUID) before the full dead-man. Manual-tier.
probe: src/ble_probe.mm src/ble_probe.plist src/cb_scanner.o
	$(CXX) $(MMSTRICT) src/ble_probe.mm src/cb_scanner.o $(FRAMEWORKS) \
	  -Wl,-sectcreate,__TEXT,__info_plist,src/ble_probe.plist -o ble-probe

# C++ objects — strict.
src/%.o: src/%.cpp
	$(CXX) $(CXXSTRICT) -c $< -o $@

# Objective-C++ BLE backend — relaxed + ARC (framework glue).
src/cb_scanner.o: src/cb_scanner.mm
	$(CXX) $(MMSTRICT) -c $< -o $@

# Shared C jsonrpc (modules/common, JE-1) — compiled as C (clang $(CSTRICT)), NOT
# clang++, so its extern "C" symbols link cleanly into this C++ module. Explicit
# rule beats the .cpp pattern; common stays cJSON-agnostic (JE-4, our -I supplies it).
../common/jsonrpc.o: ../common/jsonrpc.c
	$(CC) $(CSTRICT) -c $< -o $@

# Vendored C — relaxed.
src/vendor/%.o: src/vendor/%.c
	$(CC) $(CRELAXED) -c $< -o $@

tests/vendor/unity/unity.o: tests/vendor/unity/unity.c
	$(CC) $(CRELAXED) $(TESTINC) -c $< -o $@

tests/%.o: tests/%.cpp
	$(CXX) $(TESTCXX) -c $< -o $@

test: $(TEST_OBJS) $(UNITY_OBJ) $(CPP_OBJS) $(MM_OBJS) $(C_OBJS) $(VEND_OBJS)
	$(CXX) $(TEST_OBJS) $(UNITY_OBJ) $(CPP_OBJS) $(MM_OBJS) $(C_OBJS) $(VEND_OBJS) $(FRAMEWORKS) -o run_tests
	./run_tests

format:
	clang-format -i include/*.hpp include/*.h src/*.cpp tests/test_*.cpp

clean:
	rm -f $(BIN) companion-beacon ble-probe run_tests src/main.o $(CPP_OBJS) $(MM_OBJS) $(C_OBJS) $(VEND_OBJS) $(UNITY_OBJ) $(TEST_OBJS)
	rm -rf $(TETHER_APP)

.PHONY: test format clean companion probe app
