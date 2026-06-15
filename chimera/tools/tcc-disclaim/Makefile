# tcc-disclaim — TCC responsibility launcher (lets supervisor-spawned native daemons
# become their own TCC subject, so e.g. TETHER can raise its own Bluetooth prompt).
#   make         build the launcher
#   make test    build + run the proxy-behavior contract
#   make clean   remove build artifacts
CC     := clang
CFLAGS := -std=c17 -Wall -Wextra -Werror -O2
BIN    := tcc-disclaim

$(BIN): tcc_disclaim.c
	$(CC) $(CFLAGS) $< -o $@

test: $(BIN)
	bash test_tcc_disclaim.sh

clean:
	rm -f $(BIN)

.PHONY: test clean
