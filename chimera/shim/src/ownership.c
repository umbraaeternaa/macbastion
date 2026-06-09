/* ownership — SS-0(b) socket-ownership seam: chmod 0660 + chown root:operator_group, so
 * the user-level core (a member of operator_group) can connect while other local users
 * cannot. Root-only effect; exercised under the manual `-m privileged` tier (SH-7), not
 * in hermetic tests (chown to root needs root). */
#include "ownership.h"

#include <sys/stat.h>
#include <unistd.h>

shim_result_t ownership_apply(const char *path, gid_t operator_group) {
    if (path == NULL) {
        return SHIM_ERR;
    }
    /* chown first (it clears setuid/setgid bits), then set the mode. */
    if (chown(path, 0, operator_group) != 0) {
        return SHIM_ERR;
    }
    if (chmod(path, 0660) != 0) {
        return SHIM_ERR;
    }
    return SHIM_OK;
}
