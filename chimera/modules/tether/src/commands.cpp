/* commands — tether.* dispatch (§5 IPC API). EMIT-ONLY safety: tether.test is a
 * DRY RUN; pairing is GATED (-31004); unknown -> -31002.
 *
 * RED STUB (Slice 1): dispatch returns nullptr for every method. GREEN builds the
 * responses via jsonrpc_serialize_* and mutates the runtime (l3_armed, config). */
#include "commands.hpp"

namespace tether {

char *commands_dispatch(TetherRuntime *rt, const char *method, const cJSON *params,
                        const cJSON *id) {
    (void)rt; /* RED: GREEN reads/writes runtime (config, l3_armed, status). */
    (void)method;
    (void)params;
    (void)id;
    return nullptr; /* RED sentinel */
}

} // namespace tether
