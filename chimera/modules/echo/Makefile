# CHIMERA ECHO — Bandwidth Normalizer, shaper core (§5.2, ES-1…ES-6).
#   make test    build + run the Unity test suite
#   make format  clang-format our sources
#   make clean   remove build artifacts
#
# First slice = the pure constant-rate padding math (no external deps; the pf/BPF
# packet I/O + IPC daemon land in later slices). Our code is strict (CLAUDE.md §5);
# vendored Unity is relaxed (third-party is not held to our -Werror bar).
CC := clang

INCLUDES := -Iinclude -Isrc/vendor/cjson -I../common
STRICT   := -std=c17 -Wall -Wextra -Werror -O2 $(INCLUDES)
TESTCFL  := -std=c17 -Wall -Wextra -O2 $(INCLUDES) -Itests/vendor/unity -DUNITY_INCLUDE_DOUBLE

OUR_OBJS := $(patsubst %.c,%.o,$(wildcard src/*.c))

# Our objects — strict flags.
src/%.o: src/%.c
	$(CC) $(STRICT) -c $< -o $@

# Tests link our logic + Unity. No -Werror so a third-party macro warning never
# blocks the suite.
test:
	$(CC) $(TESTCFL) $(wildcard tests/*.c) tests/vendor/unity/unity.c \
	  $(wildcard src/*.c) ../common/jsonrpc.c src/vendor/cjson/cJSON.c -o run_tests
	./run_tests

format:
	clang-format -i include/*.h src/*.c tests/test_*.c

clean:
	rm -f src/*.o run_tests
	rm -rf run_tests.dSYM

.PHONY: test format clean
