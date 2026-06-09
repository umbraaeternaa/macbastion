/* attest — verify a connected peer IS the signed core via its audit-token code signature
 * (Slice 2b-ii). The shim issues the per-boot secret (shim.handshake) ONLY to a peer that
 * satisfies core's designated requirement — the kernel-backed way to tell core from any
 * same-uid process (peercred alone cannot). Fail-closed: any error / non-match -> 0. */
#ifndef SHIM_ATTEST_H
#define SHIM_ATTEST_H

/* 1 iff the peer on `fd` satisfies the code-signing `requirement` (a SecRequirement string,
 * e.g. core's designated requirement). 0 on NULL requirement, no peer audit token, or any
 * verification failure. */
int attest_peer_is_core(int fd, const char *requirement);

#endif /* SHIM_ATTEST_H */
