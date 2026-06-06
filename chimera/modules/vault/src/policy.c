/* VAULT policy engine — top-level composition (real, not a stub): parse the policy
 * text, evaluate against the context, free. Fail-closed: a NULL parse (syntax error,
 * unknown variable, …) returns VAULT_DENY before any evaluation. In the RED slice
 * vault_parse() always returns NULL, so this returns DENY for everything; it lights
 * up once the parser + evaluator land. */
#include "vault.h"

#include "evaluator.h"
#include "parser.h"

VaultVerdict vault_policy_evaluate(const char *policy_text, const VaultContext *ctx) {
    char err[128];
    VaultPolicy *p = vault_parse(policy_text, err, sizeof err);
    if (p == NULL) {
        return VAULT_DENY; /* fail-closed: unparseable policy is never ALLOW */
    }
    VaultVerdict verdict = vault_eval(p, ctx);
    vault_policy_free(p);
    return verdict;
}

VaultDecision vault_policy_decide(const char *policy_text, const VaultContext *ctx) {
    char err[128];
    VaultPolicy *p = vault_parse(policy_text, err, sizeof err);
    if (p == NULL) {
        VaultDecision d = {VAULT_DENY, 0}; /* fail-closed: unparseable -> DENY */
        return d;
    }
    VaultDecision d = vault_decide(p, ctx);
    vault_policy_free(p);
    return d;
}
