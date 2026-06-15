/* tether.* command dispatch (§5 IPC API). Operates on an in-memory runtime;
 * returns a malloc'd JSON-RPC response string (caller frees), using §6 error
 * codes (-31002 unknown, -31004 gated). EMIT-ONLY safety holds here too:
 *   tether.test runs the ladder as a DRY RUN — it reports stages/timings and
 *   takes NO real action and emits NO real escalation (§8 safety).
 * Pairing (tether.pair.* and unpair) is GATED (-31004): IRK storage needs
 * Keychain / Secure Enclave entitlements (the VAULT blocker), absent this slice. */
#ifndef TETHER_COMMANDS_HPP
#define TETHER_COMMANDS_HPP

#include "cJSON.h"

#include "pin.hpp"
#include "tether.hpp"

namespace tether {

/* In-memory daemon state the command layer reads/writes. */
struct TetherRuntime {
    PresenceConfig presence;
    EscalationConfig escalation;
    bool companion_paired = false; /* legacy flag; status now reflects pin.paired() */
    CompanionPin pin;              /* anti-spoof companion pin; tether.unpair clears it */
    Presence state = Presence::PRESENT;
    Stage escalation_stage = Stage::NONE;
    double rssi_smoothed = 0.0;
    bool heightened = false; /* idea #3: react sooner; base config preserved */
};

/* Dispatch one tether.* method to a malloc'd JSON-RPC response (caller frees).
 * NULL on allocation failure. Unknown method -> -31002; gated pairing -> -31004. */
char *commands_dispatch(TetherRuntime *rt, const char *method, const cJSON *params,
                        const cJSON *id);

} // namespace tether

#endif /* TETHER_COMMANDS_HPP */
