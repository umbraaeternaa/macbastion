# CHIMERA PURGE — Secure Erasure (Panic) (§5.8).
#   make         build the purge daemon binary
#   make test    build + run the Unity test suite
#   make format  clang-format our sources
#   make clean   remove build artifacts
#
# Our code is strict (CLAUDE.md §5); vendored cJSON + Unity are relaxed. The pure cores
# (plan/targets/config) + command dispatch link into both the binary and the tests. The
# real destruction engine (Keychain/Mach VM/dc zva/libsodium) is a later, gated slice;
# purge.trigger returns -31004 until then.
CC := clang

INCLUDES := -Iinclude -Isrc/vendor/cjson -I../common
STRICT   := -std=c17 -Wall -Wextra -Werror -O2 $(INCLUDES)
RELAXED  := -std=c17 -O2 $(INCLUDES)
TESTCFL  := -std=c17 -Wall -Wextra -O2 $(INCLUDES) -Itests/vendor/unity -DUNITY_INCLUDE_DOUBLE

BIN         := purge
OUR_OBJS    := $(patsubst %.c,%.o,$(wildcard src/*.c))
COMMON_OBJS := ../common/jsonrpc.o
VEND_OBJS   := src/vendor/cjson/cJSON.o

$(BIN): $(OUR_OBJS) $(COMMON_OBJS) $(VEND_OBJS)
	$(CC) $^ -o $@

# Vendored objects — relaxed flags (more specific stem wins over src/%.o).
src/vendor/%.o: src/vendor/%.c
	$(CC) $(RELAXED) -c $< -o $@

# Shared common objects — strict, our include paths (jsonrpc resolves our cJSON, JE-4).
../common/%.o: ../common/%.c
	$(CC) $(STRICT) -c $< -o $@

# Our objects — strict flags.
src/%.o: src/%.c
	$(CC) $(STRICT) -c $< -o $@

# Tests link our logic (minus main) + shared jsonrpc + vendored cJSON + Unity. No -Werror
# so a third-party macro warning never blocks the suite.
test:
	$(CC) $(TESTCFL) $(wildcard tests/*.c) tests/vendor/unity/unity.c \
	  $(filter-out src/main.c,$(wildcard src/*.c)) ../common/jsonrpc.c \
	  src/vendor/cjson/cJSON.c -o run_tests
	./run_tests

format:
	clang-format -i include/*.h src/*.c tests/test_*.c

clean:
	rm -f src/*.o src/vendor/cjson/*.o ../common/jsonrpc.o run_tests $(BIN)
	rm -rf run_tests.dSYM

.PHONY: test format clean
