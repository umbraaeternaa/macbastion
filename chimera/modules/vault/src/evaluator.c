/* VAULT policy evaluator — RED stub.
 * vault_eval() always returns VAULT_DENY (the fail-closed default), so ALLOW-case
 * tests fail and DENY-case tests pass coincidentally. GREEN walks the AST against
 * the context (typed comparisons, and/or/not, fail-closed on unknown/mismatch). */
#include "evaluator.h"

VaultVerdict vault_eval(const VaultPolicy *p, const VaultContext *ctx) {
    (void)p;
    (void)ctx;
    return VAULT_DENY;
}
