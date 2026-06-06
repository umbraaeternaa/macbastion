/* VAULT policy DSL parser — RED stub.
 * vault_parse() always returns NULL (fail-closed), so valid-parse tests fail and
 * malformed/missing tests pass coincidentally; relock accessor returns false.
 * GREEN builds the allow_when AST + relock_after duration via recursive descent. */
#include "parser.h"

#include <string.h>

struct VaultPolicy {
    int placeholder; /* GREEN replaces this with the AST + relock fields */
};

VaultPolicy *vault_parse(const char *text, char *errbuf, size_t errlen) {
    (void)text;
    if (errbuf != NULL && errlen > 0) {
        const char *msg = "parser not implemented (RED)";
        size_t n = strlen(msg);
        if (n >= errlen) {
            n = errlen - 1;
        }
        memcpy(errbuf, msg, n);
        errbuf[n] = '\0';
    }
    return NULL;
}

void vault_policy_free(VaultPolicy *p) {
    (void)p;
}

bool vault_policy_relock_seconds(const VaultPolicy *p, long *out_seconds) {
    (void)p;
    (void)out_seconds;
    return false;
}
