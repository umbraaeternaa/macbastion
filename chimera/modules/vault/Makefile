# CHIMERA VAULT — Time-Locked Storage (§5.6).
#   make         compile the engine objects (strict — the -Werror gate)
#   make test    build + run the Unity test suite
#   make format  clang-format our sources (vendored excluded)
#   make clean   remove build artifacts
#
# Slices done: the PURE policy DSL engine (lexer + parser + evaluator, incl. DEFER).
# The crypto slice adds libsodium (XChaCha20-Poly1305 + Argon2id + secure memory).
# Still NO Keychain / mount / IPC / daemon (later, gated slices); no daemon binary.
CC := clang

# libsodium is Homebrew-provided (CLAUDE.md §6 allowlist); fail fast with an
# actionable message, mirroring CHAFF's openssl@3 pattern.
SODIUM := $(shell brew --prefix libsodium 2>/dev/null)
ifeq ($(SODIUM),)
$(error libsodium not found. Install: brew install libsodium)
endif

INCLUDES := -Iinclude -I$(SODIUM)/include
STRICT   := -std=c17 -Wall -Wextra -Werror -O2 $(INCLUDES)
TESTCFL  := -std=c17 -Wall -Wextra -O2 $(INCLUDES) -Itests/vendor/unity
LDFLAGS  := -L$(SODIUM)/lib -lsodium

OUR_OBJS := $(patsubst %.c,%.o,$(wildcard src/*.c))

# Compile the engine objects under strict flags — the -Werror gate (no daemon yet).
all: $(OUR_OBJS)

src/%.o: src/%.c
	$(CC) $(STRICT) -c $< -o $@

# Tests link the engine sources + Unity + libsodium (no -Werror — vendored macros).
test:
	$(CC) $(TESTCFL) $(wildcard tests/*.c) tests/vendor/unity/unity.c \
	  $(wildcard src/*.c) $(LDFLAGS) -o run_tests
	./run_tests

format:
	clang-format -i include/*.h src/*.c tests/test_*.c

clean:
	rm -f run_tests $(OUR_OBJS)

.PHONY: all test format clean
