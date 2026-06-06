/* VAULT policy AST — the parsed allow_when expression. Shared between the parser
 * (builds it) and the evaluator (walks it). Internal to the vault module; not part
 * of the public verdict/context contract in vault.h. */
#ifndef VAULT_AST_H
#define VAULT_AST_H

#include <stddef.h>

#include "parser.h" /* opaque VaultPolicy */

/* The 8 whitelisted policy variables (§4) + a sentinel for an unrecognized name. */
typedef enum {
    VAR_HOUR,
    VAR_WEEKDAY,
    VAR_DAY_OF_MONTH,
    VAR_SECONDS_SINCE_BOOT,
    VAR_PULSE_MODE,
    VAR_TETHER,
    VAR_NETWORK_SSID,
    VAR_ORACLE_SCORE,
    VAR_UNKNOWN,
} VaultVarKind;

/* Comparison operators (§4) + a sentinel for "no operator". */
typedef enum {
    OP_EQ,
    OP_NE,
    OP_LT,
    OP_LE,
    OP_GT,
    OP_GE,
    OP_IN,
    OP_BETWEEN,
    OP_NONE,
} VaultOp;

/* Right-hand value shapes: a number, a bare word (enum value), a quoted string, a
 * list (for `in`), or a numeric range (for `between`). */
typedef enum {
    VAL_NUMBER,
    VAL_WORD,
    VAL_STRING,
    VAL_LIST,
    VAL_RANGE,
} VaultValueKind;

typedef struct {
    VaultValueKind kind;
    double number;   /* VAL_NUMBER */
    char *word;      /* VAL_WORD / VAL_STRING (owned) */
    char **list;     /* VAL_LIST (owned, list_len entries) */
    size_t list_len;
    double lo;       /* VAL_RANGE low bound */
    double hi;       /* VAL_RANGE high bound */
} VaultValue;

/* Expression node: a leaf predicate, or a not/and/or over child expressions. */
typedef enum {
    EXPR_PRED,
    EXPR_NOT,
    EXPR_AND,
    EXPR_OR,
} VaultExprKind;

typedef struct VaultExpr {
    VaultExprKind kind;
    /* EXPR_PRED */
    VaultVarKind var;
    VaultOp op;
    VaultValue value;
    /* EXPR_NOT (left only) / EXPR_AND / EXPR_OR */
    struct VaultExpr *left;
    struct VaultExpr *right;
} VaultExpr;

/* Recursively free an expression tree (and its owned values). NULL-safe. */
void vault_expr_free(VaultExpr *e);

/* The parsed allow_when AST of a policy (for the evaluator). NULL-safe. */
const VaultExpr *vault_policy_allow_expr(const VaultPolicy *p);

#endif /* VAULT_AST_H */
