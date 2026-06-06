/* VAULT policy DSL parser (§4). Recursive-descent over the lexer's token stream,
 * building an AST for the allow_when expression (predicates joined by and/or/not,
 * grouped by parens) plus the optional relock_after duration. The AST is opaque to
 * callers — the evaluator (evaluator.h) walks it. Fully auditable, ~hand-written. */
#ifndef VAULT_PARSER_H
#define VAULT_PARSER_H

#include <stdbool.h>
#include <stddef.h>

/* Opaque parsed policy. Owns its AST; free with vault_policy_free. */
typedef struct VaultPolicy VaultPolicy;

/* Parse `text` into a VaultPolicy. Returns NULL on any syntax error (and writes a
 * short message into errbuf, if errlen > 0). The caller owns the returned pointer.
 * A NULL return is the parser's fail-closed signal — the top-level treats it DENY. */
VaultPolicy *vault_parse(const char *text, char *errbuf, size_t errlen);

/* Release a parsed policy. NULL-safe. */
void vault_policy_free(VaultPolicy *p);

/* If the policy declared a relock_after block, write its duration in seconds to
 * *out_seconds and return true; otherwise return false. NULL-safe (returns false).
 * Slice 1 PARSES relock_after but does not schedule it (that is the daemon slice). */
bool vault_policy_relock_seconds(const VaultPolicy *p, long *out_seconds);

#endif /* VAULT_PARSER_H */
