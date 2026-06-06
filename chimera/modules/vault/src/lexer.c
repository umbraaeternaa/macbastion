/* VAULT policy DSL lexer — RED stub.
 * vault_lexer_next() always returns TK_EOF, so every token-shape assertion fails;
 * the empty-input test passes coincidentally. GREEN scans idents/numbers/strings/
 * operators/punctuation. */
#include "lexer.h"

void vault_lexer_init(VaultLexer *lx, const char *src) {
    lx->cur = src;
}

VaultToken vault_lexer_next(VaultLexer *lx) {
    (void)lx;
    VaultToken t = {TK_EOF, NULL, 0, 0.0};
    return t;
}
