# CHIMERA VAULT — Time-Locked Storage (§5.6).
#   make         compile the policy-engine objects (strict — the -Werror gate)
#   make test    build + run the Unity test suite
#   make format  clang-format our sources (vendored excluded)
#   make clean   remove build artifacts
#
# Slice 1 = the PURE policy DSL engine (lexer + recursive-descent parser +
# evaluator). NO libsodium, NO Keychain, NO mount, NO IPC, NO cJSON — those are
# later, gated slices. So this Makefile links NO external libraries and builds NO
# daemon binary yet; `make` compiles the engine objects under strict flags as the
# -Werror gate, `make test` runs the hermetic Unity suite.
CC := clang

INCLUDES := -Iinclude
STRICT   := -std=c17 -Wall -Wextra -Werror -O2 $(INCLUDES)
TESTCFL  := -std=c17 -Wall -Wextra -O2 $(INCLUDES) -Itests/vendor/unity

OUR_OBJS := $(patsubst %.c,%.o,$(wildcard src/*.c))

all: $(OUR_OBJS)

src/%.o: src/%.c
	$(CC) $(STRICT) -c $< -o $@

test:
	$(CC) $(TESTCFL) $(wildcard tests/*.c) tests/vendor/unity/unity.c \
	  $(wildcard src/*.c) -o run_tests
	./run_tests

format:
	clang-format -i include/*.h src/*.c tests/test_*.c

clean:
	rm -f run_tests $(OUR_OBJS)

.PHONY: all test format clean
