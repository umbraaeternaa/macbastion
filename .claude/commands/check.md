---
description: Run the full CHIMERA verification (ruff + mypy strict + pytest + native C/C++ suites) in one go
allowed-tools: Bash
---

# /check — full CHIMERA verification

Run the whole quality gate with one command, with the correct cwd / `.venv` / `TMPDIR`
already handled (avoids the recurring footguns). Use before a commit, or any time you
want to confirm the tree is green.

## Steps

1. Run `bash chimera/check.sh` (add `int` to also run the socket integration suite:
   `bash chimera/check.sh int`).
2. Report the result honestly per section: ruff, mypy --strict, pytest default, the
   native suites (chaff/mirror/vault C, tether C++, shim), and `RESULT`. If anything
   failed, quote the failing output (logs are in `/tmp/chk_<module>.log`) — do NOT
   smooth over a red result.

## Notes
- `check.sh` lives at `chimera/check.sh`; it `cd`s to `chimera/` itself, so it works
  from any cwd. Default run skips integration (socket suite is slower + needs the short
  `--basetemp`, which the `int` arg sets up).
- This is a verification gate, not a fix — it reports, it never edits.
