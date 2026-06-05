/* Peer-credential authentication (SS-6 / SH-5 (b)). The shim trusts a connection
 * only if the kernel-reported peer uid is the operator. On macOS this is
 * getsockopt(fd, SOL_LOCAL, LOCAL_PEERCRED, struct xucred) — a snapshot taken at
 * connect(), unforgeable by an unprivileged process.
 *
 * Slice 1 is peercred-ONLY (no per-boot secret): the NO-OP skeleton has zero
 * destructive effect (F3), so a same-uid caller can reach only logged no-ops.
 * The secret that distinguishes "the core" from "any operator process" is
 * mandatory before destructive ops (Slice 2, gated on code-signing — §5.5).
 *
 * Testability seam (SS-7): the resolve step is a function pointer. The real impl
 * is getsockopt; tests inject a mock to exercise the reject path without a second
 * process, and use socketpair() to exercise the accept path with real creds. */
#ifndef SHIM_PEERCRED_H
#define SHIM_PEERCRED_H

#include <sys/types.h>

#include "shim.h"

typedef struct {
    uid_t uid;
    gid_t gid;
    int valid; /* 1 once credentials were resolved */
} shim_peer_t;

/* Resolve the peer credentials of a connected socket fd via LOCAL_PEERCRED.
 * On SHIM_OK, *out is filled and out->valid == 1. */
shim_result_t peercred_resolve(int fd, shim_peer_t *out);

/* Seam type: a credential resolver. Default is peercred_resolve; tests swap in
 * a mock. */
typedef shim_result_t (*peercred_resolver_fn)(int fd, shim_peer_t *out);

/* Install a resolver (NULL restores the default getsockopt-based one). Returns
 * the previous resolver. */
peercred_resolver_fn peercred_set_resolver(peercred_resolver_fn fn);

/* Resolve via the currently-installed resolver. */
shim_result_t peercred_resolve_current(int fd, shim_peer_t *out);

/* Pure authorization predicate: 1 iff peer is valid AND peer->uid == expected.
 * Deny-by-default (returns 0 for a NULL/invalid peer). */
int peercred_authorized(const shim_peer_t *peer, uid_t expected_uid);

#endif /* SHIM_PEERCRED_H */
