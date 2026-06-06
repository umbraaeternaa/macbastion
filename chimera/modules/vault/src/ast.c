/* VAULT policy AST helpers — recursive free of an expression tree and its owned
 * value memory. Shared by the parser (cleanup on error) and the policy lifetime. */
#include "ast.h"

#include <stdlib.h>

static void value_free(VaultValue *v) {
    if (v->kind == VAL_LIST) {
        for (size_t i = 0; i < v->list_len; i++) {
            free(v->list[i]);
        }
        free(v->list);
    } else if (v->kind == VAL_WORD || v->kind == VAL_STRING) {
        free(v->word);
    }
}

void vault_expr_free(VaultExpr *e) {
    if (e == NULL) {
        return;
    }
    if (e->kind == EXPR_PRED) {
        value_free(&e->value);
    }
    vault_expr_free(e->left);
    vault_expr_free(e->right);
    free(e);
}
