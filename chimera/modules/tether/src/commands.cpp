/* commands — tether.* dispatch (§5 IPC API). Reads/writes the in-memory runtime;
 * builds JSON-RPC responses via jsonrpc_serialize_*; §6 error codes.
 *
 * EMIT-ONLY safety holds here: tether.test is a DRY RUN — it reports the ladder
 * timings and takes NO real action, emits NO escalation (§8). Pairing is GATED
 * (-31004): IRK storage needs Keychain / Secure Enclave entitlements (the VAULT
 * blocker), absent this slice. Unknown method -> -31002. */
#include "commands.hpp"

#include <cstring>

#include "events.hpp"
#include "jsonrpc.h"

namespace tether {

char *commands_dispatch(TetherRuntime *rt, const char *method, const cJSON *params,
                        const cJSON *id) {
    if (!method) {
        return jsonrpc_serialize_error(id, TETHER_RPC_CAPABILITY_MISSING, "unknown method", nullptr);
    }

    if (std::strcmp(method, "tether.status") == 0) {
        cJSON *r = cJSON_CreateObject();
        cJSON_AddStringToObject(r, "state", presence_name(rt->state));
        cJSON_AddNumberToObject(r, "rssi_smoothed", rt->rssi_smoothed);
        cJSON_AddBoolToObject(r, "companion_paired", rt->companion_paired);
        cJSON_AddStringToObject(r, "escalation_stage", stage_name(rt->escalation_stage));
        cJSON_AddBoolToObject(r, "l3_armed", rt->escalation.l3_armed);
        cJSON_AddBoolToObject(r, "heightened", rt->heightened);
        return jsonrpc_serialize_response(id, r);
    }

    if (std::strcmp(method, "tether.config.set") == 0) {
        if (params) {
            const cJSON *nt = cJSON_GetObjectItemCaseSensitive(params, "near_threshold");
            if (cJSON_IsNumber(nt)) {
                rt->presence.near_threshold = nt->valuedouble;
            }
            const cJSON *grace = cJSON_GetObjectItemCaseSensitive(params, "grace");
            if (cJSON_IsNumber(grace)) {
                rt->escalation.grace_ms = static_cast<long>(grace->valuedouble);
            }
        }
        cJSON *cfg = cJSON_CreateObject();
        cJSON_AddNumberToObject(cfg, "near_threshold", rt->presence.near_threshold);
        cJSON_AddNumberToObject(cfg, "grace", static_cast<double>(rt->escalation.grace_ms));
        cJSON *r = cJSON_CreateObject();
        cJSON_AddItemToObject(r, "config", cfg);
        return jsonrpc_serialize_response(id, r);
    }

    if (std::strcmp(method, "tether.l3.arm") == 0) {
        /* §8: arming the destructive tier requires a confirmation phrase. */
        const cJSON *p =
            params ? cJSON_GetObjectItemCaseSensitive(params, "confirmation_phrase") : nullptr;
        if (!cJSON_IsString(p) || p->valuestring[0] == '\0') {
            return jsonrpc_serialize_error(id, TETHER_RPC_PRECONDITION_FAILED,
                                           "confirmation_phrase required", nullptr);
        }
        rt->escalation.l3_armed = true;
        cJSON *r = cJSON_CreateObject();
        cJSON_AddBoolToObject(r, "ok", 1);
        cJSON_AddBoolToObject(r, "l3_armed", 1);
        return jsonrpc_serialize_response(id, r);
    }

    if (std::strcmp(method, "tether.l3.disarm") == 0) {
        rt->escalation.l3_armed = false;
        cJSON *r = cJSON_CreateObject();
        cJSON_AddBoolToObject(r, "ok", 1);
        cJSON_AddBoolToObject(r, "l3_armed", 0);
        return jsonrpc_serialize_response(id, r);
    }

    if (std::strcmp(method, "tether.escalation.cancel") == 0) {
        const Stage cancelled = rt->escalation_stage;
        rt->escalation_stage = Stage::NONE;
        cJSON *r = cJSON_CreateObject();
        cJSON_AddBoolToObject(r, "ok", 1);
        cJSON_AddStringToObject(r, "cancelled_stage", stage_name(cancelled));
        return jsonrpc_serialize_response(id, r);
    }

    if (std::strcmp(method, "tether.heighten") == 0 ||
        std::strcmp(method, "tether.relax") == 0) {
        /* idea #3 react-entrypoint: heighten tightens the grace so escalation is
         * REQUESTED sooner; relax restores the base. EMIT-ONLY is unchanged — only
         * the timing shifts, never the action. Base grace_ms is never overwritten
         * (relax is an exact, idempotent restore); the daemon mirrors the flag to
         * the live Monitor (Monitor::set_heightened) so the running ladder re-arms. */
        rt->heightened = std::strcmp(method, "tether.heighten") == 0;
        cJSON *r = cJSON_CreateObject();
        cJSON_AddBoolToObject(r, "ok", 1);
        cJSON_AddBoolToObject(r, "heightened", rt->heightened);
        cJSON_AddNumberToObject(
            r, "effective_grace_ms",
            static_cast<double>(effective_grace_ms(rt->escalation.grace_ms, rt->heightened)));
        return jsonrpc_serialize_response(id, r);
    }

    if (std::strcmp(method, "tether.test") == 0) {
        /* DRY RUN: report when each stage WOULD fire, relative to absence. NO real
         * action, NO escalation emitted (§8 safety — test the ladder, not the effect).
         * Honors the heightened flag so the dry-run reflects the live timing. */
        const EscalationConfig &ec = rt->escalation;
        const long grace = effective_grace_ms(ec.grace_ms, rt->heightened);
        cJSON *report = cJSON_CreateObject();
        cJSON_AddBoolToObject(report, "dry_run", 1);
        cJSON_AddNumberToObject(report, "l1_at_ms", static_cast<double>(grace));
        cJSON_AddNumberToObject(report, "l2_at_ms",
                                static_cast<double>(grace + ec.l1_to_l2_ms));
        if (ec.l3_armed) {
            cJSON_AddNumberToObject(
                report, "l3_at_ms",
                static_cast<double>(grace + ec.l1_to_l2_ms + ec.l2_to_l3_ms));
        }
        cJSON_AddBoolToObject(report, "l3_armed", ec.l3_armed);
        cJSON_AddBoolToObject(report, "heightened", rt->heightened);
        cJSON_AddStringToObject(report, "note", "dry-run: no escalation emitted, no action taken");
        cJSON *r = cJSON_CreateObject();
        cJSON_AddItemToObject(r, "dry_run_report", report);
        return jsonrpc_serialize_response(id, r);
    }

    if (std::strcmp(method, "tether.pair.start") == 0 ||
        std::strcmp(method, "tether.pair.confirm") == 0 ||
        std::strcmp(method, "tether.unpair") == 0) {
        return jsonrpc_serialize_error(id, TETHER_RPC_PRECONDITION_FAILED,
                                       "pairing gated: Keychain/Secure Enclave entitlements",
                                       nullptr);
    }

    return jsonrpc_serialize_error(id, TETHER_RPC_CAPABILITY_MISSING, "capability missing", nullptr);
}

} // namespace tether
