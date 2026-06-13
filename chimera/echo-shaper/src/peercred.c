/* peercred — LOCAL_PEERCRED peer authentication for the ECHO packet-shaper (§8 Amendment A1,
 * EP-5). shaper_peercred_resolve is the real macOS resolver: getsockopt(SOL_LOCAL,
 * LOCAL_PEERCRED) fills a struct xucred whose cr_uid is the peer's effective uid, snapshotted
 * by the kernel at connect() — unforgeable by an unprivileged process. The resolver seam lets
 * tests inject a mock for the reject path; authorization is deny-by-default. */
#include "peercred.h"

#include <stddef.h>
#include <sys/socket.h>
#include <sys/ucred.h>
#include <sys/un.h>

shaper_result_t shaper_peercred_resolve(int fd, shaper_peer_t *out) {
    if (out == NULL) {
        return SHAPER_ERR;
    }
    out->valid = 0;
    struct xucred cred;
    socklen_t len = sizeof(cred);
    if (getsockopt(fd, SOL_LOCAL, LOCAL_PEERCRED, &cred, &len) != 0) {
        return SHAPER_ERR;
    }
    if (cred.cr_version != XUCRED_VERSION) { /* guard against an ABI mismatch */
        return SHAPER_ERR;
    }
    out->uid = cred.cr_uid;
    out->gid = (cred.cr_ngroups > 0) ? cred.cr_groups[0] : (gid_t)-1;
    out->valid = 1;
    return SHAPER_OK;
}

static shaper_peercred_resolver_fn g_resolver = shaper_peercred_resolve;

shaper_peercred_resolver_fn shaper_peercred_set_resolver(shaper_peercred_resolver_fn fn) {
    shaper_peercred_resolver_fn prev = g_resolver;
    g_resolver = fn ? fn : shaper_peercred_resolve;
    return prev;
}

shaper_result_t shaper_peercred_resolve_current(int fd, shaper_peer_t *out) {
    return g_resolver(fd, out);
}

int shaper_peercred_authorized(const shaper_peer_t *peer, uid_t expected_uid) {
    /* Deny-by-default: a NULL or unresolved peer is never authorized. */
    return peer != NULL && peer->valid && peer->uid == expected_uid;
}
