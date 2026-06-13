# CHIMERA ECHO packet-shaper — a SEPARATE root LaunchDaemon (§8 Amendment A1, docs/ECHO_PACKET.md).
#   make test    build + run the Unity test suite
#   make format  clang-format our sources
#   make clean   remove build artifacts
#
# A1 skeleton: op whitelist + FAIL-OPEN no-op executor (no pf, no BPF, no root, no socket).
# The daemon binary + pf path + auth land in later gated slices (A1 §5). No external libs.
CC := clang

INCLUDES := -Iinclude
STRICT   := -std=c17 -Wall -Wextra -Werror -O2 $(INCLUDES)
TESTCFL  := -std=c17 -Wall -Wextra -O2 $(INCLUDES) -Itests/vendor/unity -DUNITY_INCLUDE_DOUBLE

# Tests link our logic + Unity, no -Werror (a third-party macro warning never blocks the suite).
test:
	$(CC) $(TESTCFL) $(wildcard tests/*.c) tests/vendor/unity/unity.c \
	  $(wildcard src/*.c) -o run_tests
	./run_tests

format:
	clang-format -i include/*.h src/*.c tests/test_*.c

clean:
	rm -f run_tests
	rm -rf run_tests.dSYM

.PHONY: test format clean
