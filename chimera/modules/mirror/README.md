# MIRROR — Behavioral Noise Injector (§5.4)

CHIMERA's second native module, first input-layer defense. Adds humanlike jitter
to mouse/keyboard/scroll at the CGEventTap layer to defeat behavioral biometrics
(mouse curves, keystroke dynamics) used by reCAPTCHA v3, fingerprint.js, and bank
fraud-detection. Full specification:
[`../../docs/modules/MIRROR.md`](../../docs/modules/MIRROR.md).

## Scope

- **Perturbation engine + daemon + IPC: built here** — the gaussian/jitter math,
  profiles (light/medium/heavy), password-field downgrade, exclusion list,
  per-event stats, software PRNG, and the `mirror.*` command dispatch over the
  core IPC.
- **CGEventTap install: GATED.** The real event tap requires a **code-signed
  binary** (macOS 26+) plus **Accessibility (TCC) permission** — and the chimera
  code-signing infrastructure is not built yet (§6 / §9). Until then
  `mirror.enable` returns a `-31004` error ("requires code-signing +
  Accessibility"); the engine stays IDLE and modifies nothing (fail-closed).
  Honest scope, per MANIFESTO §4. The tap is exercised manually with a signed
  build + granted TCC, never in automated CI.

## Build

```sh
make            # builds ./mirror
make test       # builds + runs the Unity suite
make format     # clang-format our sources (vendored excluded)
make clean
```

Requirements: Xcode Command Line Tools (clang, make). **No external libraries** —
system frameworks only (ApplicationServices for CGEventTap/Accessibility,
CoreFoundation for the run loop). No curl/sqlite/openssl.

## Run

```sh
./mirror             # prints version + linked framework versions
./mirror --version   # version only
```

At runtime MIRROR connects OUT to core (`~/.config/chimera/run/core.sock`) and
binds no socket of its own (star topology, §6.2 / §6.3). Config lives at
`~/.config/chimera/mirror/config.json` (profile + exclusions; plaintext — the
privacy invariant is about never persisting input *payload*, not config). No
input data ever touches disk.

## Dependencies

| Dependency | Source |
|------------|--------|
| ApplicationServices, CoreFoundation | macOS frameworks (Xcode CLT) |
| cJSON | vendored — `src/vendor/cjson/` (copied from chaff, 2026-06-04) |
| Unity | vendored — `tests/vendor/unity/` (copied from chaff, 2026-06-04) |

`ipc.c/.h` and `jsonrpc.c/.h` are copied + adapted from chaff (result type
renamed; logic unchanged, D1=C "copy now, extract to modules/common/ at the
third native module"). chaff is untouched.

## Status

Phase: bootstrap — toolchain verified end-to-end (build + smoke test). The
perturbation engine + daemon land via TDD RED -> GREEN next. The event tap is
deferred to code-signing + TCC.
