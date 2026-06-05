/* ownership — SS-0(b) socket-ownership seam (chmod 0660 + chown root:group).
 *
 * RED STUB (Slice 1): not implemented. This step is root-only and is exercised
 * solely under the manual `-m privileged` tier (SH-7), never in hermetic tests,
 * so it stays a stub returning SHIM_ERR until the GREEN privileged slice. */
#include "ownership.h"

shim_result_t ownership_apply(const char *path, gid_t operator_group) {
    (void)path;           /* RED: GREEN will chmod 0660 here. */
    (void)operator_group; /* RED: GREEN will chown root:group here. */
    return SHIM_ERR;
}
