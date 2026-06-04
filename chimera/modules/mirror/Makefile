# CHIMERA MIRROR — Behavioral Noise Injector (§5.4).
#   make         build the mirror daemon binary
#   make test    build + run the Unity test suite
#   make format  clang-format our sources (vendored excluded)
#   make clean   remove build artifacts
CC := clang

# No external libraries — system frameworks only (CGEventTap + Accessibility live
# in ApplicationServices; CoreFoundation for run loop / CF types). No curl/sqlite/openssl.
INCLUDES := -Iinclude -Isrc/vendor/cjson
STRICT  := -std=c17 -Wall -Wextra -Werror -O2 $(INCLUDES)
RELAXED := -std=c17 -O2 $(INCLUDES)
TESTCFL := -std=c17 -Wall -Wextra -O2 $(INCLUDES) -Itests/vendor/unity -DUNITY_INCLUDE_DOUBLE
LDFLAGS := -framework ApplicationServices -framework CoreFoundation

BIN       := mirror
OUR_OBJS  := $(patsubst %.c,%.o,$(filter-out src/main.c,$(wildcard src/*.c)))
VEND_OBJS := src/vendor/cjson/cJSON.o
ASM_OBJS  := $(patsubst %.S,%.o,$(wildcard src/asm/*.S))

$(BIN): src/main.o $(OUR_OBJS) $(VEND_OBJS) $(ASM_OBJS)
	$(CC) $^ $(LDFLAGS) -o $@

# Vendored objects — relaxed flags (more specific stem wins over src/%.o).
src/vendor/%.o: src/vendor/%.c
	$(CC) $(RELAXED) -c $< -o $@

# Our objects — strict flags.
src/%.o: src/%.c
	$(CC) $(STRICT) -c $< -o $@

# ARM64 assembly (mrs RNDR — deferred; rule ready for when it lands).
src/asm/%.o: src/asm/%.S
	$(CC) -c $< -o $@

# Tests link our logic (minus main) + vendored cJSON + Unity, no -Werror.
test:
	$(CC) $(TESTCFL) $(wildcard tests/*.c) tests/vendor/unity/unity.c \
	  $(filter-out src/main.c,$(wildcard src/*.c)) src/vendor/cjson/cJSON.c \
	  $(wildcard src/asm/*.S) $(LDFLAGS) -o run_tests
	./run_tests

format:
	clang-format -i include/*.h src/*.c tests/test_*.c

clean:
	rm -f $(BIN) run_tests src/main.o $(OUR_OBJS) $(VEND_OBJS) $(ASM_OBJS)

.PHONY: test format clean
