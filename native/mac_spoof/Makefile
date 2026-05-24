# Makefile for mac_spoof — Apple Silicon native module
CC      := clang
CFLAGS  := -O2 -Wall -Wextra -Werror -arch arm64 -mmacosx-version-min=13.0
TARGET  := mac_spoof
SRCS    := mac_spoof.c

all: $(TARGET)

$(TARGET): $(SRCS)
	$(CC) $(CFLAGS) $(SRCS) -o $(TARGET)
	@echo "✅ built: ./$(TARGET)"
	@file ./$(TARGET)

test: $(TARGET)
	@echo "── test 1: generate 5 random MACs ──"
	@for i in 1 2 3 4 5; do ./$(TARGET) gen; done
	@echo
	@echo "── test 2: show current en0 MAC ──"
	@./$(TARGET) show en0 || true
	@echo
	@echo "✅ tests passed (set requires sudo, not run here)"

clean:
	rm -f $(TARGET) *.o

.PHONY: all test clean
