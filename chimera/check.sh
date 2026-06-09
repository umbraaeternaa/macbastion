#!/bin/bash
# CHIMERA full verification in one command. Run from anywhere — it cd's to chimera/.
# Handles the cwd/.venv/TMPDIR footguns automatically.
#   ./check.sh        ruff + mypy(strict) + default pytest + native C/C++ suites
#   ./check.sh int    also runs the socket integration suite (slower, AF_UNIX)
cd "$(dirname "$0")" || exit 2
PY=./.venv/bin/python
RUFF=./.venv/bin/ruff
MYPY=./.venv/bin/mypy
FAIL=0
sec() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }

sec "ruff"
$RUFF check . && echo "ruff OK" || FAIL=1

sec "mypy --strict"
$MYPY core modules/oracle/oracle modules/pulse/pulse && echo "mypy OK" || FAIL=1

sec "pytest (default)"
TMPDIR=/tmp/t $PY -m pytest -q || FAIL=1

sec "native suites (C / C++)"
for m in chaff echo mirror purge vault tether; do
  if make -C "modules/$m" test >"/tmp/chk_$m.log" 2>&1; then echo "  $m  OK"; else echo "  $m  FAIL -> /tmp/chk_$m.log"; FAIL=1; fi
done
if make -C shim test >/tmp/chk_shim.log 2>&1; then echo "  shim OK"; else echo "  shim FAIL -> /tmp/chk_shim.log"; FAIL=1; fi

if [ "$1" = "int" ]; then
  sec "integration (sockets)"
  mkdir -p /tmp/tt
  TMPDIR=/tmp/t $PY -m pytest -q -m integration --basetemp=/tmp/tt || FAIL=1
fi

sec "RESULT"
if [ $FAIL -eq 0 ]; then echo "ALL GREEN"; else echo "SOMETHING FAILED"; fi
exit $FAIL
