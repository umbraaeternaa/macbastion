#!/usr/bin/env bash
# Proxy-behavior contract for tcc-disclaim (the TCC responsibility launcher).
#
# The DISCLAIM effect itself — the spawned child becoming its OWN TCC subject (so a
# supervisor-launched daemon like TETHER can raise its own Bluetooth prompt and match
# a grant keyed to its signature) — is a macOS system behavior we cannot unit-test.
# What we CAN (and must) assert is that the launcher is a FAITHFUL PROXY: it forwards
# argv to the child, propagates the child's exit status, errors on misuse, and
# forwards SIGTERM so a supervisor tracking THIS pid still controls the child.
set -u
BIN="$(cd "$(dirname "$0")" && pwd)/tcc-disclaim"
fail=0
check() { if [ "$1" = "$2" ]; then echo "  ok: $3"; else echo "  FAIL: $3 (got '$1' want '$2')"; fail=1; fi; }

if [ ! -x "$BIN" ]; then
    echo "RED: $BIN not built"
    exit 1
fi

# 1. no args -> usage, exit 2
"$BIN" >/dev/null 2>&1; check "$?" "2" "no args exits 2"

# 2. passthrough: runs the child with argv, propagates stdout + exit 0
out=$("$BIN" /bin/echo hello world); check "$?" "0" "echo exit 0"
check "$out" "hello world" "argv passthrough to child"

# 3. child exit status propagates
"$BIN" /bin/sh -c 'exit 7'; check "$?" "7" "child exit status propagates"

# 4. spawn failure -> 127
"$BIN" /no/such/program >/dev/null 2>&1; check "$?" "127" "missing program -> 127"

# 5. SIGTERM forwarded to the child (child traps TERM and exits 42)
rm -f /tmp/td_ready
"$BIN" /bin/sh -c 'trap "exit 42" TERM; : >/tmp/td_ready; while :; do :; done' &
p=$!
# Wait until the child is genuinely ready (trap installed -> readiness file written),
# so we do not signal before tcc-disclaim has spawned it + armed its forwarders. No
# sleep (blocked here): a bounded busy-spin that breaks the instant the file appears.
i=0; while [ ! -e /tmp/td_ready ] && [ "$i" -lt 5000000 ]; do i=$((i + 1)); done
rm -f /tmp/td_ready
kill -TERM "$p" 2>/dev/null
wait "$p"; check "$?" "42" "SIGTERM forwarded to child"

if [ "$fail" = 0 ]; then echo "ALL GREEN"; else echo "FAILURES"; fi
exit "$fail"
