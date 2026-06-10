# CHIMERA VAULT — Time-Locked Storage (§5.6).
#   make         build the vault daemon binary
#   make test    build + run the Unity test suite
#   make format  clang-format our sources (vendored excluded)
#   make clean   remove build artifacts
#
# The PURE engine (lexer/parser/evaluator/crypto/policy) + the VD-1 daemon (main/daemon/ipc/
# commands) build together into the `vault` binary. libsodium (Homebrew, §6) backs the crypto;
# vendored cJSON + the shared jsonrpc back the IPC. Our code is strict (-Werror); vendored
# cJSON + Unity are relaxed.
CC := clang

SODIUM := $(shell brew --prefix libsodium 2>/dev/null)
ifeq ($(SODIUM),)
$(error libsodium not found. Install: brew install libsodium)
endif

INCLUDES := -Iinclude -Isrc/vendor/cjson -I../common -I$(SODIUM)/include
STRICT   := -std=c17 -Wall -Wextra -Werror -O2 $(INCLUDES)
RELAXED  := -std=c17 -O2 $(INCLUDES)
TESTCFL  := -std=c17 -Wall -Wextra -O2 $(INCLUDES) -Itests/vendor/unity
LDFLAGS  := -L$(SODIUM)/lib -lsodium -framework Security -framework CoreFoundation

BIN         := vault
OUR_OBJS    := $(patsubst %.c,%.o,$(wildcard src/*.c))
COMMON_OBJS := ../common/jsonrpc.o
VEND_OBJS   := src/vendor/cjson/cJSON.o

$(BIN): $(OUR_OBJS) $(COMMON_OBJS) $(VEND_OBJS)
	$(CC) $^ $(LDFLAGS) -o $@

# Vendored objects — relaxed flags (more specific stem wins over src/%.o).
src/vendor/%.o: src/vendor/%.c
	$(CC) $(RELAXED) -c $< -o $@

# Shared common objects — strict, our include paths (jsonrpc resolves our cJSON, JE-4).
../common/%.o: ../common/%.c
	$(CC) $(STRICT) -c $< -o $@

# Our objects — strict flags.
src/%.o: src/%.c
	$(CC) $(STRICT) -c $< -o $@

# Tests link our logic (minus main) + shared jsonrpc + vendored cJSON + Unity + libsodium.
# No -Werror so a third-party macro warning never blocks the suite.
test:
	$(CC) $(TESTCFL) $(wildcard tests/*.c) tests/vendor/unity/unity.c \
	  $(filter-out src/main.c,$(wildcard src/*.c)) ../common/jsonrpc.c \
	  src/vendor/cjson/cJSON.c $(LDFLAGS) -o run_tests
	./run_tests

format:
	clang-format -i include/*.h src/*.c tests/test_*.c

clean:
	rm -f src/*.o src/vendor/cjson/*.o ../common/jsonrpc.o run_tests $(BIN)
	rm -rf run_tests.dSYM

.PHONY: test format clean
