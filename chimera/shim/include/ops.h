/* The 4-op whitelist and its (Slice 1 NO-OP) executor. The method→op mapping is
 * the only place free-form wire strings meet the structured §8.8 enum (SH-5 (c));
 * anything not in the whitelist maps to SHIM_OP_UNKNOWN and is refused (-31002).
 *
 * Slice 1: ops_execute performs ZERO destructive effect (F3) — it logs the
 * intent and reports a no-op. Real effects (lock / evict / reboot / killall)
 * land one at a time in Slice 3+, destructive ones last and only once the
 * per-boot secret is real (§5.4). reboot stays stubbed in autotests forever
 * (SH-11). */
#ifndef SHIM_OPS_H
#define SHIM_OPS_H

#include "shim.h"

/* Map a shim.* method string to an op enum. Returns SHIM_OP_UNKNOWN if the
 * method is not one of the four whitelisted ops. */
shim_op_t ops_from_method(const char *method);

/* The canonical wire method name for an op (e.g. "shim.lock"), or NULL for
 * SHIM_OP_UNKNOWN. */
const char *ops_method_name(shim_op_t op);

/* Execute an op. Slice 1: no real effect — sets *did_noop to 1 and returns
 * SHIM_OK. Returns SHIM_ERR_NOTFOUND for SHIM_OP_UNKNOWN. */
shim_result_t ops_execute(shim_op_t op, int *did_noop);

/* The lock action ops_execute runs for SHIM_OP_LOCK (Slice 3a). The default sleeps the
 * display via pmset — a real screen lock (with "require password after sleep" it locks),
 * NEVER run in autotests. Swappable so tests inject a recording / no-op stand-in. Returns
 * the previous action; NULL resets to the default. */
typedef shim_result_t (*ops_lock_fn)(void);
ops_lock_fn ops_set_lock_action(ops_lock_fn fn);

/* The evict action ops_execute runs for SHIM_OP_EVICT (Slice 3b, destructive, secret-gated).
 * The default deletes CHIMERA's generic-password Keychain items (service "com.umbra.chimera":
 * VAULT master secrets, TETHER IRK) from the console operator's login keychain, run in their
 * session via launchctl asuser — NEVER in autotests. Swappable for a recording / no-op
 * stand-in. Returns the previous action; NULL resets to the default. */
typedef shim_result_t (*ops_evict_fn)(void);
ops_evict_fn ops_set_evict_action(ops_evict_fn fn);

#endif /* SHIM_OPS_H */
