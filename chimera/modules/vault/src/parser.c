/* VAULT policy DSL parser (§4) — recursive-descent over the lexer's tokens, building
 * an AST for the allow_when expression plus the optional relock_after duration.
 *
 * Grammar (§4):
 *   policy       := "allow_when" ":" expression relock_block?
 *   relock_block := "relock_after" ":" <number> ("min" | "hour")
 *   expression   := or_expr
 *   or_expr      := and_expr ("or" and_expr)*
 *   and_expr     := unary ("and" unary)*
 *   unary        := "not" unary | primary
 *   primary      := "(" expression ")" | predicate
 *   predicate    := variable operator value
 *
 * Any syntax error returns NULL — the fail-closed signal the top-level maps to DENY.
 * The AST node types here are consumed by evaluator.c (same translation unit family,
 * via the shared ast.h definitions). */
#include "parser.h"

#include <stdlib.h>
#include <string.h>

#include "ast.h"
#include "lexer.h"

/* ---- parser state ---------------------------------------------------------- */

typedef struct {
    VaultLexer lx;
    VaultToken tok; /* lookahead (current token) */
    bool failed;
    char *errbuf;
    size_t errlen;
} Parser;

static void fail(Parser *p, const char *msg) {
    if (!p->failed) {
        p->failed = true;
        if (p->errbuf != NULL && p->errlen > 0) {
            size_t n = strlen(msg);
            if (n >= p->errlen) {
                n = p->errlen - 1;
            }
            memcpy(p->errbuf, msg, n);
            p->errbuf[n] = '\0';
        }
    }
}

static void advance(Parser *p) {
    p->tok = vault_lexer_next(&p->lx);
    if (p->tok.kind == TK_ERROR) {
        fail(p, "lex error");
    }
}

static bool tok_is_ident(const VaultToken *t, const char *word) {
    size_t n = strlen(word);
    return t->kind == TK_IDENT && t->len == n && memcmp(t->start, word, n) == 0;
}

/* ---- forward decls --------------------------------------------------------- */

static VaultExpr *parse_expression(Parser *p);

/* ---- value + predicate ----------------------------------------------------- */

static VaultVarKind variable_kind(const VaultToken *t) {
    if (tok_is_ident(t, "hour")) return VAR_HOUR;
    if (tok_is_ident(t, "weekday")) return VAR_WEEKDAY;
    if (tok_is_ident(t, "day_of_month")) return VAR_DAY_OF_MONTH;
    if (tok_is_ident(t, "seconds_since_boot")) return VAR_SECONDS_SINCE_BOOT;
    if (tok_is_ident(t, "pulse_mode")) return VAR_PULSE_MODE;
    if (tok_is_ident(t, "tether")) return VAR_TETHER;
    if (tok_is_ident(t, "network_ssid")) return VAR_NETWORK_SSID;
    if (tok_is_ident(t, "oracle_score")) return VAR_ORACLE_SCORE;
    return VAR_UNKNOWN;
}

static VaultOp operator_kind(const VaultToken *t) {
    switch (t->kind) {
    case TK_EQ: return OP_EQ;
    case TK_NE: return OP_NE;
    case TK_LT: return OP_LT;
    case TK_LE: return OP_LE;
    case TK_GT: return OP_GT;
    case TK_GE: return OP_GE;
    default: break;
    }
    if (tok_is_ident(t, "in")) return OP_IN;
    if (tok_is_ident(t, "between")) return OP_BETWEEN;
    return OP_NONE;
}

/* Copy a token's text into a freshly-malloc'd NUL-terminated string. */
static char *dup_token(const VaultToken *t) {
    char *s = malloc(t->len + 1);
    if (s == NULL) {
        return NULL;
    }
    memcpy(s, t->start, t->len);
    s[t->len] = '\0';
    return s;
}

/* Parse the right-hand value for an operator. `in` -> a [list] of words; `between`
 * -> two numbers (lo, hi); scalar ops -> a number, an enum/word ident, or a string. */
static bool parse_value(Parser *p, VaultOp op, VaultValue *out) {
    memset(out, 0, sizeof(*out));

    if (op == OP_IN) {
        if (p->tok.kind != TK_LBRACKET) {
            fail(p, "expected [ after in");
            return false;
        }
        advance(p);
        size_t cap = 4;
        out->list = malloc(cap * sizeof(char *));
        if (out->list == NULL) {
            fail(p, "oom");
            return false;
        }
        out->kind = VAL_LIST;
        out->list_len = 0;
        while (p->tok.kind != TK_RBRACKET) {
            if (p->tok.kind != TK_IDENT && p->tok.kind != TK_STRING) {
                fail(p, "expected list item");
                return false;
            }
            if (out->list_len == cap) {
                cap *= 2;
                char **grown = realloc(out->list, cap * sizeof(char *));
                if (grown == NULL) {
                    fail(p, "oom");
                    return false;
                }
                out->list = grown;
            }
            out->list[out->list_len] = dup_token(&p->tok);
            if (out->list[out->list_len] == NULL) {
                fail(p, "oom");
                return false;
            }
            out->list_len++;
            advance(p);
            if (p->tok.kind == TK_COMMA) {
                advance(p);
            } else if (p->tok.kind != TK_RBRACKET) {
                fail(p, "expected , or ] in list");
                return false;
            }
        }
        advance(p); /* consume ] */
        return true;
    }

    if (op == OP_BETWEEN) {
        if (p->tok.kind != TK_NUMBER) {
            fail(p, "expected number after between");
            return false;
        }
        out->kind = VAL_RANGE;
        out->lo = p->tok.number;
        advance(p);
        if (!tok_is_ident(&p->tok, "and")) {
            fail(p, "expected and in between");
            return false;
        }
        advance(p);
        if (p->tok.kind != TK_NUMBER) {
            fail(p, "expected number after and");
            return false;
        }
        out->hi = p->tok.number;
        advance(p);
        return true;
    }

    /* Scalar value: number, enum/word ident, or quoted string. */
    if (p->tok.kind == TK_NUMBER) {
        out->kind = VAL_NUMBER;
        out->number = p->tok.number;
        advance(p);
        return true;
    }
    if (p->tok.kind == TK_STRING) {
        out->kind = VAL_STRING;
        out->word = dup_token(&p->tok);
        if (out->word == NULL) {
            fail(p, "oom");
            return false;
        }
        advance(p);
        return true;
    }
    if (p->tok.kind == TK_IDENT) {
        out->kind = VAL_WORD;
        out->word = dup_token(&p->tok);
        if (out->word == NULL) {
            fail(p, "oom");
            return false;
        }
        advance(p);
        return true;
    }
    fail(p, "expected a value");
    return false;
}

static VaultExpr *expr_new(VaultExprKind kind) {
    VaultExpr *e = calloc(1, sizeof(VaultExpr));
    if (e != NULL) {
        e->kind = kind;
    }
    return e; /* caller checks NULL */
}

static VaultExpr *parse_predicate(Parser *p) {
    VaultVarKind var = variable_kind(&p->tok);
    if (var == VAR_UNKNOWN) {
        fail(p, "unknown variable");
        return NULL;
    }
    advance(p);
    VaultOp op = operator_kind(&p->tok);
    if (op == OP_NONE) {
        fail(p, "expected operator");
        return NULL;
    }
    advance(p);
    VaultExpr *e = expr_new(EXPR_PRED);
    if (e == NULL) {
        fail(p, "oom");
        return NULL;
    }
    e->kind = EXPR_PRED;
    e->var = var;
    e->op = op;
    if (!parse_value(p, op, &e->value)) {
        vault_expr_free(e);
        return NULL;
    }
    return e;
}

static VaultExpr *parse_primary(Parser *p) {
    if (p->tok.kind == TK_LPAREN) {
        advance(p);
        VaultExpr *inner = parse_expression(p);
        if (inner == NULL) {
            return NULL;
        }
        if (p->tok.kind != TK_RPAREN) {
            fail(p, "expected )");
            vault_expr_free(inner);
            return NULL;
        }
        advance(p);
        return inner;
    }
    return parse_predicate(p);
}

static VaultExpr *parse_unary(Parser *p) {
    if (tok_is_ident(&p->tok, "not")) {
        advance(p);
        VaultExpr *operand = parse_unary(p);
        if (operand == NULL) {
            return NULL;
        }
        VaultExpr *e = expr_new(EXPR_NOT);
        if (e == NULL) {
            fail(p, "oom");
            vault_expr_free(operand);
            return NULL;
        }
        e->kind = EXPR_NOT;
        e->left = operand;
        return e;
    }
    return parse_primary(p);
}

static VaultExpr *parse_and(Parser *p) {
    VaultExpr *left = parse_unary(p);
    if (left == NULL) {
        return NULL;
    }
    while (tok_is_ident(&p->tok, "and")) {
        advance(p);
        VaultExpr *right = parse_unary(p);
        if (right == NULL) {
            vault_expr_free(left);
            return NULL;
        }
        VaultExpr *e = expr_new(EXPR_AND);
        if (e == NULL) {
            fail(p, "oom");
            vault_expr_free(left);
            vault_expr_free(right);
            return NULL;
        }
        e->kind = EXPR_AND;
        e->left = left;
        e->right = right;
        left = e;
    }
    return left;
}

static VaultExpr *parse_expression(Parser *p) {
    VaultExpr *left = parse_and(p);
    if (left == NULL) {
        return NULL;
    }
    while (tok_is_ident(&p->tok, "or")) {
        advance(p);
        VaultExpr *right = parse_and(p);
        if (right == NULL) {
            vault_expr_free(left);
            return NULL;
        }
        VaultExpr *e = expr_new(EXPR_OR);
        if (e == NULL) {
            fail(p, "oom");
            vault_expr_free(left);
            vault_expr_free(right);
            return NULL;
        }
        e->kind = EXPR_OR;
        e->left = left;
        e->right = right;
        left = e;
    }
    return left;
}

/* relock_after: <number> ("min" | "hour") — sets *out_seconds, returns true if the
 * (optional) block was present and well-formed. A malformed block fails the parse. */
static bool parse_relock(Parser *p, bool *present, long *out_seconds) {
    *present = false;
    if (!tok_is_ident(&p->tok, "relock_after")) {
        return true; /* no relock block — fine */
    }
    advance(p);
    if (p->tok.kind != TK_COLON) {
        fail(p, "expected : after relock_after");
        return false;
    }
    advance(p);
    if (p->tok.kind != TK_NUMBER) {
        fail(p, "expected duration number");
        return false;
    }
    long n = (long)p->tok.number;
    advance(p);
    long mult;
    if (tok_is_ident(&p->tok, "min")) {
        mult = 60;
    } else if (tok_is_ident(&p->tok, "hour")) {
        mult = 3600;
    } else {
        fail(p, "expected min or hour");
        return false;
    }
    advance(p);
    *present = true;
    *out_seconds = n * mult;
    return true;
}

/* ---- public API ------------------------------------------------------------ */

struct VaultPolicy {
    VaultExpr *allow;
    bool has_relock;
    long relock_seconds;
};

VaultPolicy *vault_parse(const char *text, char *errbuf, size_t errlen) {
    if (errbuf != NULL && errlen > 0) {
        errbuf[0] = '\0';
    }
    Parser p;
    vault_lexer_init(&p.lx, text);
    p.failed = false;
    p.errbuf = errbuf;
    p.errlen = errlen;
    advance(&p); /* prime lookahead */

    if (!tok_is_ident(&p.tok, "allow_when")) {
        fail(&p, "expected allow_when");
        return NULL;
    }
    advance(&p);
    if (p.tok.kind != TK_COLON) {
        fail(&p, "expected : after allow_when");
        return NULL;
    }
    advance(&p);

    VaultExpr *allow = parse_expression(&p);
    if (allow == NULL || p.failed) {
        vault_expr_free(allow);
        return NULL;
    }

    bool has_relock = false;
    long relock_seconds = 0;
    if (!parse_relock(&p, &has_relock, &relock_seconds)) {
        vault_expr_free(allow);
        return NULL;
    }

    /* Trailing tokens after a complete policy are a syntax error (fail-closed). */
    if (p.tok.kind != TK_EOF) {
        fail(&p, "unexpected trailing tokens");
        vault_expr_free(allow);
        return NULL;
    }

    VaultPolicy *pol = calloc(1, sizeof(VaultPolicy));
    if (pol == NULL) {
        vault_expr_free(allow);
        return NULL;
    }
    pol->allow = allow;
    pol->has_relock = has_relock;
    pol->relock_seconds = relock_seconds;
    return pol;
}

void vault_policy_free(VaultPolicy *p) {
    if (p == NULL) {
        return;
    }
    vault_expr_free(p->allow);
    free(p);
}

bool vault_policy_relock_seconds(const VaultPolicy *p, long *out_seconds) {
    if (p == NULL || !p->has_relock) {
        return false;
    }
    *out_seconds = p->relock_seconds;
    return true;
}

const VaultExpr *vault_policy_allow_expr(const VaultPolicy *p) {
    return p == NULL ? NULL : p->allow;
}
