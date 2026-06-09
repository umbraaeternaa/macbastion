# CHIMERA PURGE — Secure Erasure (Panic), dry-run planner (§5.8, PG-1…PG-5).
#   make test    build + run the Unity test suite
#   make format  clang-format our sources
#   make clean   remove build artifacts
#
# First slice = the pure dry-run PLANNER + the §8 honest-wipe classification (destroys
# NOTHING). The real destruction (Keychain eviction, Mach VM, ARM64 dc zva, libsodium,
# the daemon + purge.arm/trigger) lands in later, gated slices. Our code is strict
# (CLAUDE.md §5); vendored Unity is relaxed.
CC := clang

INCLUDES := -Iinclude -Isrc/vendor/cjson -I../common
STRICT   := -std=c17 -Wall -Wextra -Werror -O2 $(INCLUDES)
TESTCFL  := -std=c17 -Wall -Wextra -O2 $(INCLUDES) -Itests/vendor/unity -DUNITY_INCLUDE_DOUBLE

src/%.o: src/%.c
	$(CC) $(STRICT) -c $< -o $@

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
