/* TETHER — Proximity Dead-Man Switch (§5.7). C++ umbrella: version, the shared
 * engine enums, and config structs. The wire/result codes live in the C-safe
 * tether_result.h (shared with the C jsonrpc layer).
 *
 * Slice 1 scope (honest accounting, MANIFESTO §4): the presence/classify/
 * escalation engine + event payloads + tether.* dispatch are real and hermetic
 * (BLE source + clock behind seams). Escalation is EMIT-ONLY — TETHER computes
 * which stage to request and emits tether.escalation; CORE enforces L1 (shim),
 * L2 (VAULT), L3 (PURGE) (spec §5). The CoreBluetooth .mm source and IRK/Keychain
 * pairing are GATED (HW + TCC + code-signing) and absent this slice. */
#ifndef TETHER_HPP
#define TETHER_HPP

#include "tether_result.h"

namespace tether {

inline constexpr const char *VERSION = "0.1.0-alpha";

/* Presence state machine (§3 steady state). */
enum class Presence { PRESENT, FRINGE, ABSENT };

/* Disappearance classification (§3 anti-weaponization). */
enum class Disappearance { NONE, FADE, CLEAN_DROP, INSTANT_DROP };

/* Escalation ladder stage (§3). NONE = nothing due yet. */
enum class Stage { NONE, L1, L2, L3 };

/* Presence FSM tuning (§3 defaults). */
struct PresenceConfig {
    double near_threshold = -70.0; /* dBm; smoothed RSSI >= this => "near" */
    int absent_ticks = 5;          /* consecutive missed ticks => ABSENT (~10s @2s) */
    int recover_ticks = 3;         /* M near ticks => recovered */
};

/* Escalation ladder tuning (§3 defaults, milliseconds). */
struct EscalationConfig {
    long grace_ms = 30000;           /* ABSENT confirmed -> L1 */
    long l1_to_l2_ms = 60000;        /* L1 -> L2 */
    long l2_to_l3_ms = 300000;       /* L2 -> L3 (opt-in) */
    long suspicious_delay_ms = 60000; /* added on INSTANT_DROP (slows, never speeds) */
    bool l3_armed = false;           /* L3 opt-in, default DISABLED (§8 safety) */
};

/* Heightened-sensitivity divisor (idea #3): on an upstream anomaly TETHER may be
 * asked to react sooner; heighten divides the grace, never the base config — so a
 * later relax restores it exactly. EMIT-ONLY is unchanged: a tighter grace only
 * makes the ladder REQUEST escalation earlier; core still enforces the action. */
inline constexpr int HEIGHTEN_FACTOR = 2;

/* Effective grace given the base and the heightened flag. Pure — used by both the
 * command layer (status/dry-run) and the Monitor (ladder re-arm) so they agree on
 * timing. Divides the base by HEIGHTEN_FACTOR when heightened; the base is never
 * mutated, so relax restores it exactly (idempotent). */
inline constexpr long effective_grace_ms(long base_grace_ms, bool heightened) {
    return heightened ? base_grace_ms / HEIGHTEN_FACTOR : base_grace_ms;
}

} // namespace tether

#endif /* TETHER_HPP */
