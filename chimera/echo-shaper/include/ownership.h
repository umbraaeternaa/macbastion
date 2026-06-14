/* ownership — socket-ownership seam for the ECHO packet-shaper (C1, mirrors the shim's SS-0(b)).
 * In production the shaper runs as root and its UNIX socket must be chmod 0660 + chown
 * root:operator_group so the non-root core (a member of that group) can connect while other
 * local users cannot — a 0600 root socket would be unreachable by the core. Root-only effect,
 * applied solely under the `-m privileged` tier: the success path is manual-tier (chown to root
 * needs root), the failure paths (NULL, non-root EPERM) are tested hermetically. */
#ifndef SHAPER_OWNERSHIP_H
#define SHAPER_OWNERSHIP_H

#include <sys/types.h>

#include "shaper.h" /* shaper_result_t */

/* Apply socket ownership at `path`: chown to root:operator_group, then chmod 0660. Returns
 * SHAPER_OK on success, SHAPER_ERR on failure (e.g. not running as root). */
shaper_result_t shaper_ownership_apply(const char *path, gid_t operator_group);

#endif /* SHAPER_OWNERSHIP_H */
