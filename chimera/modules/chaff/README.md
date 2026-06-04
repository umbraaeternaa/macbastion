# CHAFF — Traffic Obfuscator (§5.1)

CHIMERA's first native module. Generates contextual decoy HTTPS traffic that
statistically masks the operator's real browsing patterns from passive
observers. Full specification: [`../../docs/modules/CHAFF.md`](../../docs/modules/CHAFF.md).

## Scope

- **Phase B — Generation: IMPLEMENTED here** (userspace decoy traffic via
  libcurl; no root).
- **Phase A — Profiling: DEFERRED.** It observes real outbound connections via
  `pf`/`dtrace`, which require root — that belongs to the privileged shim
  (§7.10 / §8.8), not yet built. Honest scope, per MANIFESTO §4. Until then
  CHAFF generates against a synthetic flat profile (equal category weights);
  `chaff.profile.*` commands return a `requires_privileged_shim` error.

## Build

```sh
make            # builds ./chaff
make test       # builds + runs the Unity suite
make format     # clang-format our sources (vendored excluded)
make clean
```

Requirements:
- Xcode Command Line Tools (clang, make) — provides libcurl + sqlite3 via the SDK.
- `brew install openssl@3` — for the Fernet (AES-128-CBC + HMAC-SHA256) at-rest
  encryption. The Makefile resolves it via `brew --prefix openssl@3` and fails
  fast if absent.

## Run

```sh
./chaff             # prints version + linked library versions
./chaff --version   # version only
```

At runtime CHAFF connects OUT to core (`~/.config/chimera/run/core.sock` for
commands, `events.sock` for events) and binds no socket of its own
(star topology, §6.2 / §6.3). Config and state live under
`~/.config/chimera/chaff/`.

## Dependencies

| Dependency | Source |
|------------|--------|
| libcurl, sqlite3 | macOS SDK (Xcode CLT) |
| openssl@3 | Homebrew |
| cJSON | vendored — `src/vendor/cjson/` |
| Unity | vendored — `tests/vendor/unity/` |

Vendored 2026-06-04 from GitHub releases: **Unity 2.6.1**
(ThrowTheSwitch/Unity), **cJSON 1.7.18** (DaveGamble/cJSON). Vendored files are
excluded from `make format` and from our `-Werror` bar.

## Status

Phase B bootstrap — toolchain verified end-to-end (build + smoke test).
Generation logic lands via the TDD RED → GREEN cycle in subsequent commits.
