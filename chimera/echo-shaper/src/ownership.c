/* ownership — socket-ownership seam (C1, mirrors shim SS-0(b)): chown root:operator_group then
 * chmod 0660, so the non-root core (a member of operator_group) can reach the root shaper's
 * UNIX socket while other local users cannot. Root-only effect, applied under the `-m
 * privileged` tier; chown-to-root needs root, so only the failure paths are hermetic. */
#include "ownership.h"

#include <sys/stat.h>
#include <unistd.h>

shaper_result_t shaper_ownership_apply(const char *path, gid_t operator_group) {
    if (path == NULL) {
        return SHAPER_ERR;
    }
    /* chown first (it clears any setuid/setgid bits), then set the mode. */
    if (chown(path, 0, operator_group) != 0) {
        return SHAPER_ERR;
    }
    if (chmod(path, 0660) != 0) {
        return SHAPER_ERR;
    }
    return SHAPER_OK;
}
