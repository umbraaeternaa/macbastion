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

/* Evaluate a parsed policy against `ctx`. NULL policy / NULL ctx -> VAULT_DENY. */
VaultVerdict vault_eval(const VaultPolicy *p, const VaultContext *ctx);

#endif /* VAULT_EVALUATOR_H */
