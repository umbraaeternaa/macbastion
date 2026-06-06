/* VAULT policy evaluator (§3 step 3, §4) — walks a parsed allow_when AST against a
 * concrete context and returns ALLOW or DENY (slice 1 never returns DEFER).
 *
 * FAIL-CLOSED is the security invariant: a NULL policy, an unknown variable, a
 * type-mismatched predicate (e.g. a numeric operator on an enum variable, or `in`
 * on a numeric), or a value from a not-running module that the policy did not
 * explicitly opt into (`... unknown`) all evaluate the predicate to FALSE — and an
 * allow_when that is not TRUE is DENY. There is no path where uncertainty opens.
 *
 * Internally each predicate yields a tri-state {TRUE, FALSE, ERROR}; ERROR (type
 * mismatch / unknown variable) is treated as FALSE for the boolean algebra AND
 * forces the whole evaluation closed, so `not (<error>)` cannot flip to ALLOW. */
#include "evaluator.h"

#include <string.h>

#include "ast.h"

typedef enum { PRED_FALSE = 0, PRED_TRUE = 1, PRED_ERROR = 2 } PredResult;

/* ---- context accessors (typed) -------------------------------------------- */

static const char *weekday_name(VaultWeekday w) {
    switch (w) {
    case VWD_MON: return "mon";
    case VWD_TUE: return "tue";
    case VWD_WED: return "wed";
    case VWD_THU: return "thu";
    case VWD_FRI: return "fri";
    case VWD_SAT: return "sat";
    case VWD_SUN: return "sun";
    }
    return "";
}

static const char *pulse_name(VaultPulse p) {
    switch (p) {
    case VPULSE_NORMAL: return "normal";
    case VPULSE_CAUTION: return "caution";
    case VPULSE_TIRED: return "tired";
    case VPULSE_EXHAUSTED: return "exhausted";
    case VPULSE_UNKNOWN: return "unknown";
    }
    return "unknown";
}

static const char *tether_name(VaultTether t) {
    switch (t) {
    case VTETHER_PRESENT: return "present";
    case VTETHER_ABSENT: return "absent";
    case VTETHER_UNKNOWN: return "unknown";
    }
    return "unknown";
}

/* Is this a numeric variable? (the others are enum/string). */
static bool var_is_numeric(VaultVarKind v) {
    return v == VAR_HOUR || v == VAR_DAY_OF_MONTH || v == VAR_SECONDS_SINCE_BOOT ||
           v == VAR_ORACLE_SCORE;
}

/* Numeric value of a numeric variable; sets *known=false when the source module is
 * down (oracle_score only — clock-derived vars are always known). */
static double numeric_value(VaultVarKind v, const VaultContext *c, bool *known) {
    *known = true;
    switch (v) {
    case VAR_HOUR: return (double)c->hour;
    case VAR_DAY_OF_MONTH: return (double)c->day_of_month;
    case VAR_SECONDS_SINCE_BOOT: return (double)c->seconds_since_boot;
    case VAR_ORACLE_SCORE:
        *known = c->oracle_known;
        return c->oracle_score;
    default:
        *known = false;
        return 0.0;
    }
}

/* String form of an enum/string variable; NULL when unavailable (network down).
 * For enum variables the value is always a name (possibly "unknown"). */
static const char *word_value(VaultVarKind v, const VaultContext *c) {
    switch (v) {
    case VAR_WEEKDAY: return weekday_name(c->weekday);
    case VAR_PULSE_MODE: return pulse_name(c->pulse_mode);
    case VAR_TETHER: return tether_name(c->tether);
    case VAR_NETWORK_SSID: return c->network_ssid; /* may be NULL */
    default: return NULL;
    }
}

/* ---- predicate evaluation ------------------------------------------------- */

static PredResult eval_numeric(VaultOp op, double lhs, const VaultValue *val) {
    if (op == OP_BETWEEN) {
        if (val->kind != VAL_RANGE) {
            return PRED_ERROR;
        }
        return (lhs >= val->lo && lhs <= val->hi) ? PRED_TRUE : PRED_FALSE;
    }
    if (op == OP_IN) {
        return PRED_ERROR; /* `in` is for enum/string lists, not numbers */
    }
    if (val->kind != VAL_NUMBER) {
        return PRED_ERROR; /* numeric comparator needs a numeric literal */
    }
    double rhs = val->number;
    switch (op) {
    case OP_EQ: return (lhs == rhs) ? PRED_TRUE : PRED_FALSE;
    case OP_NE: return (lhs != rhs) ? PRED_TRUE : PRED_FALSE;
    case OP_LT: return (lhs < rhs) ? PRED_TRUE : PRED_FALSE;
    case OP_LE: return (lhs <= rhs) ? PRED_TRUE : PRED_FALSE;
    case OP_GT: return (lhs > rhs) ? PRED_TRUE : PRED_FALSE;
    case OP_GE: return (lhs >= rhs) ? PRED_TRUE : PRED_FALSE;
    default: return PRED_ERROR;
    }
}

static PredResult eval_word(VaultOp op, const char *lhs, const VaultValue *val) {
    if (lhs == NULL) {
        return PRED_ERROR; /* variable unavailable (e.g. SSID with network down) */
    }
    if (op == OP_EQ || op == OP_NE) {
        if (val->kind != VAL_WORD && val->kind != VAL_STRING) {
            return PRED_ERROR;
        }
        bool equal = strcmp(lhs, val->word) == 0;
        if (op == OP_NE) {
            equal = !equal;
        }
        return equal ? PRED_TRUE : PRED_FALSE;
    }
    if (op == OP_IN) {
        if (val->kind != VAL_LIST) {
            return PRED_ERROR;
        }
        for (size_t i = 0; i < val->list_len; i++) {
            if (strcmp(lhs, val->list[i]) == 0) {
                return PRED_TRUE;
            }
        }
        return PRED_FALSE;
    }
    return PRED_ERROR; /* <, <=, >, >=, between on an enum/string -> type mismatch */
}

static PredResult eval_predicate(const VaultExpr *e, const VaultContext *c) {
    if (e->var == VAR_UNKNOWN) {
        return PRED_ERROR;
    }
    if (var_is_numeric(e->var)) {
        bool known = false;
        double lhs = numeric_value(e->var, c, &known);
        if (!known) {
            return PRED_ERROR; /* module down -> fail closed */
        }
        return eval_numeric(e->op, lhs, &e->value);
    }
    /* enum / string variable */
    const char *lhs = word_value(e->var, c);
    return eval_word(e->op, lhs, &e->value);
}

/* Walk the expression. ERROR propagates: any errored predicate forces the whole
 * tree closed (returns ERROR), so `not`, `and`, `or` can never launder an error
 * into ALLOW. The top level treats anything other than TRUE as DENY. */
static PredResult eval_expr(const VaultExpr *e, const VaultContext *c) {
    if (e == NULL) {
        return PRED_ERROR;
    }
    switch (e->kind) {
    case EXPR_PRED:
        return eval_predicate(e, c);
    case EXPR_NOT: {
        PredResult r = eval_expr(e->left, c);
        if (r == PRED_ERROR) {
            return PRED_ERROR; /* fail-closed: never flip an error to TRUE */
        }
        return (r == PRED_TRUE) ? PRED_FALSE : PRED_TRUE;
    }
    case EXPR_AND: {
        PredResult l = eval_expr(e->left, c);
        PredResult r = eval_expr(e->right, c);
        if (l == PRED_ERROR || r == PRED_ERROR) {
            return PRED_ERROR;
        }
        return (l == PRED_TRUE && r == PRED_TRUE) ? PRED_TRUE : PRED_FALSE;
    }
    case EXPR_OR: {
        PredResult l = eval_expr(e->left, c);
        PredResult r = eval_expr(e->right, c);
        if (l == PRED_ERROR || r == PRED_ERROR) {
            return PRED_ERROR; /* conservative: a malformed branch fails closed */
        }
        return (l == PRED_TRUE || r == PRED_TRUE) ? PRED_TRUE : PRED_FALSE;
    }
    }
    return PRED_ERROR;
}

VaultVerdict vault_eval(const VaultPolicy *p, const VaultContext *ctx) {
    if (p == NULL || ctx == NULL) {
        return VAULT_DENY;
    }
    const VaultExpr *allow = vault_policy_allow_expr(p);
    return (eval_expr(allow, ctx) == PRED_TRUE) ? VAULT_ALLOW : VAULT_DENY;
}

VaultDecision vault_decide(const VaultPolicy *p, const VaultContext *ctx) {
    (void)p;
    (void)ctx;
    /* RED stub: always {DENY, 0}. GREEN evaluates now (TRUE->ALLOW, ERROR->DENY)
     * and, when FALSE, projects wall-clock time forward up to the cap to find the
     * first ALLOW (DEFER seconds) or gives up (DENY). */
    VaultDecision d = {VAULT_DENY, 0};
    return d;
}
