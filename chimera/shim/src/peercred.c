/* peercred — LOCAL_PEERCRED peer authentication (SS-6 / SH-5 (b)).
 *
 * peercred_resolve is the real macOS resolver: getsockopt(SOL_LOCAL,
 * LOCAL_PEERCRED) fills a struct xucred whose cr_uid is the peer's effective uid
 * snapshotted by the kernel at connect() — unforgeable by an unprivileged
 * process. The resolver-swap seam (set_resolver/resolve_current) is kept so tests
 * can inject a mock for the reject path without a second process (SS-7).
 *
 * Slice 1 is peercred-ONLY (no per-boot secret): the NO-OP skeleton has zero
 * destructive effect (F3), so a same-uid caller reaches only logged no-ops. The
 * secret that distinguishes "the core" from "any operator process" is mandatory
 * before destructive ops (Slice 2, gated on code-signing — §5.5). */
#include "peercred.h"

#include <stddef.h>
#include <sys/socket.h>
#include <sys/ucred.h>
#include <sys/un.h>

shim_result_t peercred_resolve(int fd, shim_peer_t *out) {
    if (!out) {
        return SHIM_ERR;
    }
    out->valid = 0;
    struct xucred cred;
    socklen_t len = sizeof(cred);
    if (getsockopt(fd, SOL_LOCAL, LOCAL_PEERCRED, &cred, &len) != 0) {
        return SHIM_ERR_IO;
    }
    /* Guard against an ABI mismatch in the returned credential struct. */
    if (cred.cr_version != XUCRED_VERSION) {
        return SHIM_ERR;
    }
    out->uid = cred.cr_uid;
    out->gid = (cred.cr_ngroups > 0) ? cred.cr_groups[0] : (gid_t)-1;
    out->valid = 1;
    return SHIM_OK;
}

/* Seam plumbing: the currently-installed resolver, default = the getsockopt one. */
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
    /* Deny-by-default: a NULL or unresolved peer is never authorized. */
    return peer && peer->valid && peer->uid == expected_uid;
}
