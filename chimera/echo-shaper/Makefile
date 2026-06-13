# CHIMERA ECHO packet-shaper — a SEPARATE root LaunchDaemon (§8 Amendment A1, docs/ECHO_PACKET.md).
#   make test    build + run the Unity test suite
#   make format  clang-format our sources
#   make clean   remove build artifacts
#
# A1 skeleton: op whitelist + FAIL-OPEN no-op executor (no pf, no BPF, no root, no socket).
# The daemon binary + pf path + auth land in later gated slices (A1 §5). No external libs.
CC := clang

# -Isrc/vendor/cjson + -I../modules/common: the shared jsonrpc (JE-1) for the dispatch layer.
# Still NO network libs — UNIX-domain sockets only, like the shim (§8.8).
INCLUDES := -Iinclude -Isrc/vendor/cjson -I../modules/common
STRICT   := -std=c17 -Wall -Wextra -Werror -O2 $(INCLUDES)
TESTCFL  := -std=c17 -Wall -Wextra -O2 $(INCLUDES) -Itests/vendor/unity -DUNITY_INCLUDE_DOUBLE

# Tests link our logic + shared jsonrpc + vendored cJSON + Unity, no -Werror (a third-party
# macro warning never blocks the suite).
test:
	$(CC) $(TESTCFL) $(wildcard tests/*.c) tests/vendor/unity/unity.c \
	  $(wildcard src/*.c) ../modules/common/jsonrpc.c src/vendor/cjson/cJSON.c -o run_tests
	./run_tests

format:
	clang-format -i include/*.h src/*.c tests/test_*.c

clean:
	rm -f run_tests
	rm -rf run_tests.dSYM

.PHONY: test format clean
