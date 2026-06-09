# CHIMERA privileged shim — root LaunchDaemon, 4 enumerated ops (§8.8 / SHIM.md).
#   make         build the shim daemon binary
#   make test    build + run the Unity test suite
#   make format  clang-format our sources (vendored excluded)
#   make clean   remove build artifacts
#
# Slice 1 (SHIM.md §5.4): NO-OP security skeleton — socket server + LOCAL_PEERCRED
# (peercred-only, SS-6) + op-enum whitelist + ping/pong. No secret (Slice 2),
# no launchd plist (SH-8), no code-signing (Slice 2), no real ops (Slice 3+).
CC := clang

# No external libraries — POSIX sockets + getsockopt(LOCAL_PEERCRED) only. The
# shim NEVER opens network sockets (§8.8); UNIX-domain only. No curl/sqlite/openssl,
# no frameworks (Keychain eviction is Slice 3+, gated separately).
# -I../modules/common: the shared jsonrpc (JE-1 extract; shim is one level up
# from modules/, hence ../modules/common, not ../common).
INCLUDES := -Iinclude -Isrc/vendor/cjson -I../modules/common
STRICT  := -std=c17 -Wall -Wextra -Werror -O2 $(INCLUDES)
RELAXED := -std=c17 -O2 $(INCLUDES)
TESTCFL := -std=c17 -Wall -Wextra -O2 $(INCLUDES) -Itests/vendor/unity -DUNITY_INCLUDE_DOUBLE

# Security + CoreFoundation: audit-token SecCode peer attestation (attest.c, 2b-ii). Still
# NO network libs — UNIX-domain sockets only (§8.8).
FRAMEWORKS := -framework Security -framework CoreFoundation

BIN        := chimera-shim
OUR_OBJS   := $(patsubst %.c,%.o,$(filter-out src/main.c,$(wildcard src/*.c)))
COMMON_OBJS := ../modules/common/jsonrpc.o   # shared jsonrpc (JE-1 extract; no longer copied)
VEND_OBJS  := src/vendor/cjson/cJSON.o

$(BIN): src/main.o $(OUR_OBJS) $(COMMON_OBJS) $(VEND_OBJS)
	$(CC) $^ $(FRAMEWORKS) -o $@

# Vendored objects — relaxed flags (more specific stem wins over src/%.o).
src/vendor/%.o: src/vendor/%.c
	$(CC) $(RELAXED) -c $< -o $@

# Our objects — strict flags.
src/%.o: src/%.c
	$(CC) $(STRICT) -c $< -o $@

# Shared common objects — strict flags, our include paths (so the shared
# jsonrpc.c resolves our vendored cJSON; common stays cJSON-agnostic, JE-4).
../modules/common/%.o: ../modules/common/%.c
	$(CC) $(STRICT) -c $< -o $@

# Tests link our logic (minus main) + vendored cJSON + Unity, no -Werror.
test:
	$(CC) $(TESTCFL) $(wildcard tests/*.c) tests/vendor/unity/unity.c \
	  $(filter-out src/main.c,$(wildcard src/*.c)) ../modules/common/jsonrpc.c \
	  src/vendor/cjson/cJSON.c \
	  $(FRAMEWORKS) -o run_tests
	./run_tests

format:
	clang-format -i include/*.h src/*.c tests/test_*.c

clean:
	rm -f $(BIN) run_tests src/main.o $(OUR_OBJS) $(COMMON_OBJS) $(VEND_OBJS)

.PHONY: test format clean
