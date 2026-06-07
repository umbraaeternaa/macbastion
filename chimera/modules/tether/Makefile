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

BIN       := tether
CPP_OBJS  := $(patsubst %.cpp,%.o,$(filter-out src/main.cpp,$(wildcard src/*.cpp)))
C_OBJS    := ../common/jsonrpc.o           # shared jsonrpc (JE-1 extract; ends TE-7b, was the 4th copy)
VEND_OBJS := src/vendor/cjson/cJSON.o
UNITY_OBJ := tests/vendor/unity/unity.o
TEST_OBJS := $(patsubst %.cpp,%.o,$(wildcard tests/*.cpp))

$(BIN): src/main.o $(CPP_OBJS) $(C_OBJS) $(VEND_OBJS)
	$(CXX) $^ -o $@

# C++ objects — strict.
src/%.o: src/%.cpp
	$(CXX) $(CXXSTRICT) -c $< -o $@

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

test: $(TEST_OBJS) $(UNITY_OBJ) $(CPP_OBJS) $(C_OBJS) $(VEND_OBJS)
	$(CXX) $(TEST_OBJS) $(UNITY_OBJ) $(CPP_OBJS) $(C_OBJS) $(VEND_OBJS) -o run_tests
	./run_tests

format:
	clang-format -i include/*.hpp include/*.h src/*.cpp tests/test_*.cpp

clean:
	rm -f $(BIN) run_tests src/main.o $(CPP_OBJS) $(C_OBJS) $(VEND_OBJS) $(UNITY_OBJ) $(TEST_OBJS)

.PHONY: test format clean
