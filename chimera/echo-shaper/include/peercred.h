/* peercred — LOCAL_PEERCRED peer authentication for the ECHO packet-shaper (§8 Amendment A1,
 * EP-5). The shaper trusts a connection only if the kernel-reported peer uid is the operator.
 * On macOS that is getsockopt(fd, SOL_LOCAL, LOCAL_PEERCRED, struct xucred) — a snapshot taken
 * at connect(), unforgeable by an unprivileged process. The resolve step is a function-pointer
 * seam so tests exercise the accept path with a real socketpair and the reject path with a
 * mock — no second process, no root. Authorization is deny-by-default. */
#ifndef SHAPER_PEERCRED_H
#define SHAPER_PEERCRED_H

#include <sys/types.h>

#include "shaper.h" /* shaper_result_t */

typedef struct {
    uid_t uid;
    gid_t gid;
    int valid; /* 1 once credentials were resolved */
} shaper_peer_t;

/* Resolve the peer credentials of a connected fd via LOCAL_PEERCRED. On SHAPER_OK, *out is
 * filled and out->valid == 1. */
shaper_result_t shaper_peercred_resolve(int fd, shaper_peer_t *out);

/* Resolver seam: default is shaper_peercred_resolve; tests swap in a mock. */
typedef shaper_result_t (*shaper_peercred_resolver_fn)(int fd, shaper_peer_t *out);

/* Install a resolver (NULL restores the default getsockopt-based one). Returns the previous. */
shaper_peercred_resolver_fn shaper_peercred_set_resolver(shaper_peercred_resolver_fn fn);

/* Resolve via the currently-installed resolver. */
shaper_result_t shaper_peercred_resolve_current(int fd, shaper_peer_t *out);

/* Pure predicate: 1 iff peer is valid AND peer->uid == expected. Deny-by-default (0 for a
 * NULL/invalid peer). */
int shaper_peercred_authorized(const shaper_peer_t *peer, uid_t expected_uid);

#endif /* SHAPER_PEERCRED_H */
