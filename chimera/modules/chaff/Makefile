# CHIMERA CHAFF — Traffic Obfuscator, Phase B generation (§5.1).
#   make         build the chaff daemon binary
#   make test    build + run the Unity test suite
#   make format   clang-format our sources (vendored excluded)
#   make clean    remove build artifacts
CC := clang

# openssl@3 is Homebrew-provided; fail fast with an actionable message.
OPENSSL := $(shell brew --prefix openssl@3 2>/dev/null)
ifeq ($(OPENSSL),)
$(error openssl@3 not found. Install: brew install openssl@3)
endif

# libcurl + sqlite3 ship in the macOS SDK; openssl@3 from Homebrew.
# -I../common: the shared jsonrpc (JE-1 extract; no longer a per-module copy).
INCLUDES := -Iinclude -Isrc/vendor/cjson -I../common -I$(OPENSSL)/include
# Our production code is strict (CLAUDE.md §5). Vendored + tests are relaxed:
# third-party code is not held to our -Werror bar.
STRICT  := -std=c17 -Wall -Wextra -Werror -O2 $(INCLUDES)
RELAXED := -std=c17 -O2 $(INCLUDES)
TESTCFL := -std=c17 -Wall -Wextra -O2 $(INCLUDES) -Itests/vendor/unity -DUNITY_INCLUDE_DOUBLE
LDFLAGS := -lcurl -lsqlite3 -L$(OPENSSL)/lib -lcrypto

BIN        := chaff
OUR_OBJS   := $(patsubst %.c,%.o,$(filter-out src/main.c,$(wildcard src/*.c)))
COMMON_OBJS := ../common/jsonrpc.o   # shared jsonrpc (JE-1 extract; no longer copied)
VEND_OBJS  := src/vendor/cjson/cJSON.o
ASM_OBJS   := $(patsubst %.S,%.o,$(wildcard src/asm/*.S))

$(BIN): src/main.o $(OUR_OBJS) $(COMMON_OBJS) $(VEND_OBJS) $(ASM_OBJS)
	$(CC) $^ $(LDFLAGS) -o $@

# Vendored objects — relaxed flags (more specific stem wins over src/%.o).
src/vendor/%.o: src/vendor/%.c
	$(CC) $(RELAXED) -c $< -o $@

# Our objects — strict flags.
src/%.o: src/%.c
	$(CC) $(STRICT) -c $< -o $@

# Shared common objects — strict flags, our include paths (so the shared
# jsonrpc.c resolves our vendored cJSON; common stays cJSON-agnostic, JE-4).
../common/%.o: ../common/%.c
	$(CC) $(STRICT) -c $< -o $@

# ARM64 assembly (CNTVCT_EL0 timing, added in the generation phase).
src/asm/%.o: src/asm/%.S
	$(CC) -c $< -o $@

# Tests link our logic (minus main) + vendored cJSON + Unity. No -Werror so a
# third-party macro warning never blocks the suite.
test:
	$(CC) $(TESTCFL) $(wildcard tests/*.c) tests/vendor/unity/unity.c \
	  $(filter-out src/main.c,$(wildcard src/*.c)) ../common/jsonrpc.c \
	  src/vendor/cjson/cJSON.c \
	  $(wildcard src/asm/*.S) $(LDFLAGS) -o run_tests
	./run_tests

format:
	clang-format -i include/*.h src/*.c tests/test_*.c

clean:
	rm -f $(BIN) run_tests src/main.o $(OUR_OBJS) $(COMMON_OBJS) $(VEND_OBJS) $(ASM_OBJS)

.PHONY: test format clean
