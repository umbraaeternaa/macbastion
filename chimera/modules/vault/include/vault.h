/* VAULT — Time-Locked Storage (§5.6). Slice 1: the PURE policy engine — lexer +
 * recursive-descent parser + evaluator for the policy DSL (§4). No libsodium, no
 * Keychain, no mount, no IPC — those are later, gated slices. This file declares
 * the public verdict + context contract; the engine is hermetic and Unity-tested.
 *
 * SECURITY INVARIANT (fail-closed, §4): any uncertainty — parse error, unknown
 * variable, type mismatch, a value from a not-running module without an explicit
 * `unknown` opt-out — evaluates to DENY. VAULT is locked unless EXPLICITLY allowed. */
#ifndef VAULT_H
#define VAULT_H

#include <stdbool.h>

#define VAULT_VERSION "0.1.0-alpha"

/* Policy verdict (§3). DENY = 0 so the zero value and every uncertain path is
 * fail-closed. DEFER is declared for a stable contract; slice 1's evaluator only
 * returns ALLOW/DENY (the DEFER temporal projection is a later slice). */
typedef enum {
    VAULT_DENY = 0,
    VAULT_ALLOW = 1,
    VAULT_DEFER = 2,
} VaultVerdict;

/* Enum policy variables (§4). Each carries an UNKNOWN member so a not-running
 * module fails closed unless the policy explicitly lists unknown. */
typedef enum {
    VWD_MON, VWD_TUE, VWD_WED, VWD_THU, VWD_FRI, VWD_SAT, VWD_SUN,
} VaultWeekday;

typedef enum {
    VPULSE_NORMAL, VPULSE_CAUTION, VPULSE_TIRED, VPULSE_EXHAUSTED, VPULSE_UNKNOWN,
} VaultPulse;

typedef enum {
    VTETHER_PRESENT, VTETHER_ABSENT, VTETHER_UNKNOWN,
} VaultTether;

/* Evaluation context (§3 step 2). System variables (hour / weekday / day_of_month
 * / seconds_since_boot) are always known; module variables may be unknown
 * (VPULSE_UNKNOWN / VTETHER_UNKNOWN, NULL ssid, or oracle_known = false) and then
 * fail closed unless the policy opts in. Slice 1 injects this hermetically; the
 * real gathering (sysctl kern.boottime + module state) is a later seam. */
typedef struct {
    int hour;                 /* 0..23 */
    VaultWeekday weekday;
    int day_of_month;         /* 1..31 */
    long seconds_since_boot;
    VaultPulse pulse_mode;    /* may be VPULSE_UNKNOWN (PULSE not running) */
    VaultTether tether;       /* may be VTETHER_UNKNOWN (TETHER not running) */
    const char *network_ssid; /* NULL = none / unknown */
    double oracle_score;      /* valid only when oracle_known */
    bool oracle_known;        /* false if ORACLE not running */
} VaultContext;

/* Top-level: parse `policy_text`, evaluate against `ctx`, free. Fail-closed — any
 * parse error / unknown variable / type mismatch returns VAULT_DENY. Slice 1
 * returns ALLOW/DENY (never DEFER yet). */
VaultVerdict vault_policy_evaluate(const char *policy_text, const VaultContext *ctx);

#endif /* VAULT_H */
