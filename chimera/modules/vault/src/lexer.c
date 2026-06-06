/* VAULT policy DSL lexer (§4). Scans the policy text into a flat token stream:
 * identifiers (keywords / variables / enum values), numbers (integer or float),
 * "quoted" strings, the comparison operators, and the structural punctuation.
 * Whitespace (incl. newlines) separates tokens; there are no comments in the DSL.
 * Pure — no allocation, tokens point back into the source buffer. */
#include "lexer.h"

#include <stdbool.h>

static bool is_space(char c) {
    return c == ' ' || c == '\t' || c == '\r' || c == '\n';
}

static bool is_digit(char c) {
    return c >= '0' && c <= '9';
}

/* Identifier start/continue: letters, digits (continue only), underscore. Variable
 * names and enum values are all [a-zA-Z_][a-zA-Z0-9_]*. */
static bool is_ident_start(char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_';
}

static bool is_ident_cont(char c) {
    return is_ident_start(c) || is_digit(c);
}

void vault_lexer_init(VaultLexer *lx, const char *src) {
    lx->cur = src;
}

static VaultToken make(VaultTokenKind kind, const char *start, size_t len) {
    VaultToken t;
    t.kind = kind;
    t.start = start;
    t.len = len;
    t.number = 0.0;
    return t;
}

VaultToken vault_lexer_next(VaultLexer *lx) {
    while (is_space(*lx->cur)) {
        lx->cur++;
    }
    const char *s = lx->cur;
    char c = *s;

    if (c == '\0') {
        return make(TK_EOF, s, 0);
    }

    /* Identifier: keyword / variable / enum value. */
    if (is_ident_start(c)) {
        const char *p = s;
        while (is_ident_cont(*p)) {
            p++;
        }
        lx->cur = p;
        return make(TK_IDENT, s, (size_t)(p - s));
    }

    /* Number: digits with an optional single fractional part. A trailing unit
     * (e.g. "min" in "30min") is left for the next call as a separate ident. */
    if (is_digit(c)) {
        const char *p = s;
        while (is_digit(*p)) {
            p++;
        }
        if (*p == '.' && is_digit(p[1])) {
            p++;
            while (is_digit(*p)) {
                p++;
            }
        }
        VaultToken t = make(TK_NUMBER, s, (size_t)(p - s));
        double value = 0.0;
        double frac = 0.0;
        double scale = 1.0;
        bool in_frac = false;
        for (const char *q = s; q < p; q++) {
            if (*q == '.') {
                in_frac = true;
                continue;
            }
            if (in_frac) {
                scale *= 10.0;
                frac += (double)(*q - '0') / scale;
            } else {
                value = value * 10.0 + (double)(*q - '0');
            }
        }
        t.number = value + frac;
        lx->cur = p;
        return t;
    }

    /* Quoted string: content between double quotes (quotes stripped from start/len).
     * An unterminated string is an error. */
    if (c == '"') {
        const char *p = s + 1;
        while (*p != '\0' && *p != '"') {
            p++;
        }
        if (*p != '"') {
            lx->cur = p; /* hit EOF */
            return make(TK_ERROR, s, (size_t)(p - s));
        }
        VaultToken t = make(TK_STRING, s + 1, (size_t)(p - (s + 1)));
        lx->cur = p + 1; /* consume the closing quote */
        return t;
    }

    /* Two-char and single-char operators / punctuation. */
    switch (c) {
    case '=':
        if (s[1] == '=') {
            lx->cur = s + 2;
            return make(TK_EQ, s, 2);
        }
        lx->cur = s + 1;
        return make(TK_ERROR, s, 1); /* bare '=' is not valid */
    case '!':
        if (s[1] == '=') {
            lx->cur = s + 2;
            return make(TK_NE, s, 2);
        }
        lx->cur = s + 1;
        return make(TK_ERROR, s, 1);
    case '<':
        if (s[1] == '=') {
            lx->cur = s + 2;
            return make(TK_LE, s, 2);
        }
        lx->cur = s + 1;
        return make(TK_LT, s, 1);
    case '>':
        if (s[1] == '=') {
            lx->cur = s + 2;
            return make(TK_GE, s, 2);
        }
        lx->cur = s + 1;
        return make(TK_GT, s, 1);
    case ':':
        lx->cur = s + 1;
        return make(TK_COLON, s, 1);
    case '(':
        lx->cur = s + 1;
        return make(TK_LPAREN, s, 1);
    case ')':
        lx->cur = s + 1;
        return make(TK_RPAREN, s, 1);
    case '[':
        lx->cur = s + 1;
        return make(TK_LBRACKET, s, 1);
    case ']':
        lx->cur = s + 1;
        return make(TK_RBRACKET, s, 1);
    case ',':
        lx->cur = s + 1;
        return make(TK_COMMA, s, 1);
    default:
        lx->cur = s + 1;
        return make(TK_ERROR, s, 1);
    }
}
