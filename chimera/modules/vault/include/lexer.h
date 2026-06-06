/* VAULT policy DSL lexer (§4). Tokenizes the policy text into a flat token stream
 * the recursive-descent parser consumes. Keywords (allow_when, relock_after, and,
 * or, not, in, between, min, hour), variable names, and enum values are ALL emitted
 * as TK_IDENT — the parser disambiguates by text + position. Pure, no allocation. */
#ifndef VAULT_LEXER_H
#define VAULT_LEXER_H

#include <stddef.h>

typedef enum {
    TK_IDENT,     /* keyword, variable name, or enum value (hour, mon, normal, and) */
    TK_NUMBER,    /* integer or float literal (value in VaultToken.number) */
    TK_STRING,    /* "quoted" — start/len cover the content, quotes stripped */
    TK_COLON,     /* : */
    TK_LPAREN,    /* ( */
    TK_RPAREN,    /* ) */
    TK_LBRACKET,  /* [ */
    TK_RBRACKET,  /* ] */
    TK_COMMA,     /* , */
    TK_EQ,        /* == */
    TK_NE,        /* != */
    TK_LT,        /* <  */
    TK_LE,        /* <= */
    TK_GT,        /* >  */
    TK_GE,        /* >= */
    TK_EOF,       /* end of input */
    TK_ERROR,     /* unrecognized byte / malformed token */
} VaultTokenKind;

typedef struct {
    VaultTokenKind kind;
    const char *start; /* points into the source buffer (not NUL-terminated) */
    size_t len;        /* token length in the source */
    double number;     /* parsed value when kind == TK_NUMBER */
} VaultToken;

typedef struct {
    const char *cur; /* current scan position in the source */
} VaultLexer;

/* Bind the lexer to a NUL-terminated source buffer (no copy). */
void vault_lexer_init(VaultLexer *lx, const char *src);

/* Return the next token; TK_EOF at end, TK_ERROR on a bad byte. */
VaultToken vault_lexer_next(VaultLexer *lx);

#endif /* VAULT_LEXER_H */
