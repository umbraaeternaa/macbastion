/* SS-0(b) socket-ownership seam. In production the shim runs as root and the
 * socket must be chmod 0660 + chown root:operatorgroup so the user-level core
 * (member of the operator group) can connect while other local users cannot —
 * a 0600 root socket would be unreachable by the non-root core (Finding F1).
 *
 * This step is root-only and is NOT exercised by the hermetic non-root skeleton
 * (SS-7): in Slice 1 the socket is left owner-only (0600 self) under a tmp path,
 * and the real ownership is applied solely under the manual `-m privileged`
 * tier (SH-7). Kept behind a seam so tests need no root. */
#ifndef SHIM_OWNERSHIP_H
#define SHIM_OWNERSHIP_H

#include <sys/types.h>

#include "shim.h"

/* Apply SS-0(b) to the bound socket at `path`: chmod 0660 then chown to
 * root:operator_group. Returns SHIM_OK on success, SHIM_ERR on failure (e.g.
 * not running as root). Real effect lives in the `-m privileged` tier. */
shim_result_t ownership_apply(const char *path, gid_t operator_group);

#endif /* SHIM_OWNERSHIP_H */
