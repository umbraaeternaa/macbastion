/* VAULT policy evaluator (§3 step 3, §4). Walks a parsed policy's allow_when AST
 * against a concrete VaultContext and returns a verdict. Pure — no clock, no
 * syscalls, no module queries; the caller supplies the context (hermetic).
 *
 * Fail-closed: a NULL policy, an unknown/unavailable variable without an explicit
 * `unknown` opt-out, or a type mismatch yields VAULT_DENY. Slice 1 returns
 * ALLOW/DENY only (DEFER is a later slice). */
#ifndef VAULT_EVALUATOR_H
#define VAULT_EVALUATOR_H

#include "parser.h"
#include "vault.h"

/* Evaluate a parsed policy against `ctx` — the INSTANTANEOUS check. NULL policy /
 * NULL ctx -> VAULT_DENY. Returns ALLOW/DENY only (never DEFER). Unchanged from
 * slice 1; the DEFER projection lives in vault_decide. */
VaultVerdict vault_eval(const VaultPolicy *p, const VaultContext *ctx);

/* Decide with FORWARD TIME PROJECTION: if the policy is not allowed now but a
 * future wall-clock time (within the cap) would make it ALLOW, return DEFER with
 * the seconds to wait. Holds non-time variables constant (only time advances), so
 * a block that time cannot lift -> DENY. A base ERROR (unknown var / type mismatch
 * / module down) -> DENY, never DEFER. NULL policy / NULL ctx -> {DENY, 0}. */
VaultDecision vault_decide(const VaultPolicy *p, const VaultContext *ctx);

#endif /* VAULT_EVALUATOR_H */
