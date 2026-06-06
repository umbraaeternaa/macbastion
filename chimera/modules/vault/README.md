# VAULT — Time-Locked Storage (§5.6)

Encrypted storage whose decryption key materializes only when the operator's
pre-declared **policy** is satisfied (time / presence / module-state). State-gated,
not key-gated: if the policy denies, no key exists anywhere. See `docs/modules/VAULT.md`.

C17 + libsodium + macOS Keychain/Secure Enclave (later slices). Local-only, no
network.

## Status — Slice 1: policy DSL engine (in progress)

Slice 1 is the **pure policy engine** — the heart of VAULT's uniqueness — with zero
platform dependencies:

- **lexer** (`src/lexer.c`) — tokenizes the policy DSL (§4)
- **parser** (`src/parser.c`) — recursive-descent → AST (allow_when expression +
  relock_after duration)
- **evaluator** (`src/evaluator.c`) — walks the AST against an injected context →
  verdict
- **policy** (`src/policy.c`) — top-level parse → evaluate → free

**Security invariant — fail-closed (§4):** any uncertainty (parse error, unknown
variable, type mismatch, a value from a not-running module without an explicit
`unknown` opt-out) evaluates to **DENY**. VAULT is locked unless explicitly allowed.

Verdict is `ALLOW | DENY | DEFER`; slice 1's evaluator returns ALLOW/DENY only
(the DEFER temporal projection is a later slice). `relock_after` is parsed but not
yet scheduled.

NOT in slice 1 (deferred, gated): libsodium crypto (AES-256-GCM + Argon2id),
Keychain/Secure-Enclave master secret, `mount_tmpfs`, kqueue relock, IPC/daemon.

```
make        # compile the engine objects (strict, -Werror gate)
make test   # build + run the Unity suite
```

No external libraries, no daemon binary yet — pure C policy engine.

## Honest accounting (MANIFESTO §4)

Real now: the policy DSL lexer/parser/evaluator (hermetic, Unity-tested). Gated:
everything touching the platform (crypto deps, Keychain entitlements + Secure
Enclave, tmpfs mount privileges, IPC). No stubs that pretend — the engine is real;
the gated pieces are absent and named.
