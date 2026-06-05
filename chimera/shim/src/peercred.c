/* peercred — LOCAL_PEERCRED peer authentication (SS-6 / SH-5 (b)).
 *
 * RED STUB (Slice 1): the resolver-swap plumbing (set_resolver / resolve_current)
 * is REAL — tests need it to inject a mock. But the two pieces of logic under
 * test are stubs:
 *   - peercred_resolve   (the real getsockopt LOCAL_PEERCRED) returns SHIM_ERR
 *   - peercred_authorized (the uid predicate) denies everything (returns 0)
 * GREEN implements getsockopt(SOL_LOCAL, LOCAL_PEERCRED, struct xucred) and the
 * `valid && uid == expected` predicate. */
#include "peercred.h"

shim_result_t peercred_resolve(int fd, shim_peer_t *out) {
    (void)fd; /* RED: GREEN will getsockopt(SOL_LOCAL, LOCAL_PEERCRED) here. */
    if (out) {
        out->valid = 0;
    }
    return SHIM_ERR;
}

/* Seam plumbing (real): the currently-installed resolver, default = the
 * getsockopt-based one above. */
static peercred_resolver_fn g_resolver = peercred_resolve;

peercred_resolver_fn peercred_set_resolver(peercred_resolver_fn fn) {
    peercred_resolver_fn prev = g_resolver;
    g_resolver = fn ? fn : peercred_resolve;
    return prev;
}

shim_result_t peercred_resolve_current(int fd, shim_peer_t *out) {
    return g_resolver(fd, out);
}

int peercred_authorized(const shim_peer_t *peer, uid_t expected_uid) {
    (void)peer;         /* RED: GREEN returns peer->valid && peer->uid == expected. */
    (void)expected_uid; /* RED: deny-by-default until implemented. */
    return 0;
}
