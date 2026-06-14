# CHIMERA ECHO packet-shaper — a SEPARATE root LaunchDaemon (§8 Amendment A1, docs/ECHO_PACKET.md).
#   make         build the shaper daemon binary (chimera-echo-shaper)
#   make test    build + run the Unity test suite
#   make format  clang-format our sources
#   make clean   remove build artifacts
#
# The daemon ties the units (server + peercred + protocol + secret) into one serve-one-request
# loop — ROOT-FREE: UNIX-domain socket only (§8.8), no pf/BPF/root yet. The real pf path lands
# in a later gated slice on a throwaway anchor, with per-command root approval (A1 §5). No
# external libs, and (unlike the shim) no -framework — the shaper does no SecCode attestation.
CC := clang

# -Isrc/vendor/cjson + -I../modules/common: the shared jsonrpc (JE-1) for the dispatch layer.
# Still NO network libs — UNIX-domain sockets only, like the shim (§8.8).
INCLUDES := -Iinclude -Isrc/vendor/cjson -I../modules/common
STRICT   := -std=c17 -Wall -Wextra -Werror -O2 $(INCLUDES)
RELAXED  := -std=c17 -O2 $(INCLUDES)
TESTCFL  := -std=c17 -Wall -Wextra -O2 $(INCLUDES) -Itests/vendor/unity -DUNITY_INCLUDE_DOUBLE

BIN         := chimera-echo-shaper
OUR_OBJS    := $(patsubst %.c,%.o,$(filter-out src/main.c,$(wildcard src/*.c)))
COMMON_OBJS := ../modules/common/jsonrpc.o   # shared jsonrpc (JE-1 extract; no longer copied)
VEND_OBJS   := src/vendor/cjson/cJSON.o

$(BIN): src/main.o $(OUR_OBJS) $(COMMON_OBJS) $(VEND_OBJS)
	$(CC) $^ -o $@

# Vendored objects — relaxed flags (more specific stem wins over src/%.o).
src/vendor/%.o: src/vendor/%.c
	$(CC) $(RELAXED) -c $< -o $@

# Our objects — strict flags.
src/%.o: src/%.c
	$(CC) $(STRICT) -c $< -o $@

# Shared common objects — strict flags, our include paths (so the shared jsonrpc.c resolves
# our vendored cJSON; common stays cJSON-agnostic, JE-4).
../modules/common/%.o: ../modules/common/%.c
	$(CC) $(STRICT) -c $< -o $@

# Tests link our logic (minus main) + shared jsonrpc + vendored cJSON + Unity, no -Werror (a
# third-party macro warning never blocks the suite).
test:
	$(CC) $(TESTCFL) $(wildcard tests/*.c) tests/vendor/unity/unity.c \
	  $(filter-out src/main.c,$(wildcard src/*.c)) ../modules/common/jsonrpc.c \
	  src/vendor/cjson/cJSON.c -o run_tests
	./run_tests

format:
	clang-format -i include/*.h src/*.c tests/test_*.c

clean:
	rm -f $(BIN) run_tests src/main.o $(OUR_OBJS) $(COMMON_OBJS) $(VEND_OBJS)
	rm -rf run_tests.dSYM

.PHONY: test format clean
