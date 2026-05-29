"""Tests for errors module (§6.5 — JSON-RPC + CHIMERA error codes)."""

import pytest
from core.errors import (
    ERROR_MESSAGES,
    JSONRPC_INTERNAL_ERROR,
    JSONRPC_INVALID_PARAMS,
    JSONRPC_INVALID_REQUEST,
    JSONRPC_METHOD_NOT_FOUND,
    JSONRPC_PARSE_ERROR,
    ChimeraError,
    RpcError,
)

# ---------------------------------------------------------------------------
# JSON-RPC reserved codes (§6.5 — must match the spec exactly)
# ---------------------------------------------------------------------------


class TestJsonRpcReservedCodes:
    """The five JSON-RPC 2.0 reserved error codes have exact values per spec."""

    def test_parse_error_is_minus_32700(self) -> None:
        assert JSONRPC_PARSE_ERROR == -32700

    def test_invalid_request_is_minus_32600(self) -> None:
        assert JSONRPC_INVALID_REQUEST == -32600

    def test_method_not_found_is_minus_32601(self) -> None:
        assert JSONRPC_METHOD_NOT_FOUND == -32601

    def test_invalid_params_is_minus_32602(self) -> None:
        assert JSONRPC_INVALID_PARAMS == -32602

    def test_internal_error_is_minus_32603(self) -> None:
        assert JSONRPC_INTERNAL_ERROR == -32603

    def test_reserved_codes_are_integers(self) -> None:
        for code in (
            JSONRPC_PARSE_ERROR,
            JSONRPC_INVALID_REQUEST,
            JSONRPC_METHOD_NOT_FOUND,
            JSONRPC_INVALID_PARAMS,
            JSONRPC_INTERNAL_ERROR,
        ):
            assert isinstance(code, int)


# ---------------------------------------------------------------------------
# CHIMERA application codes (-31000 block, §6.5)
# ---------------------------------------------------------------------------


class TestChimeraErrorCodes:
    """ChimeraError IntEnum holds the eight CHIMERA application codes."""

    def test_module_offline_is_minus_31000(self) -> None:
        assert ChimeraError.MODULE_OFFLINE == -31000

    def test_module_timeout_is_minus_31001(self) -> None:
        assert ChimeraError.MODULE_TIMEOUT == -31001

    def test_capability_missing_is_minus_31002(self) -> None:
        assert ChimeraError.CAPABILITY_MISSING == -31002

    def test_denied_by_policy_is_minus_31003(self) -> None:
        assert ChimeraError.DENIED_BY_POLICY == -31003

    def test_precondition_failed_is_minus_31004(self) -> None:
        assert ChimeraError.PRECONDITION_FAILED == -31004

    def test_fail_closed_is_minus_31005(self) -> None:
        assert ChimeraError.FAIL_CLOSED == -31005

    def test_rate_limited_is_minus_31006(self) -> None:
        assert ChimeraError.RATE_LIMITED == -31006

    def test_not_authorized_is_minus_31007(self) -> None:
        assert ChimeraError.NOT_AUTHORIZED == -31007

    def test_chimera_error_is_int_enum(self) -> None:
        # Must behave as both IntEnum and int — per rishennya A.
        assert isinstance(ChimeraError.MODULE_OFFLINE, int)
        assert ChimeraError.MODULE_OFFLINE.value == -31000

    def test_chimera_error_has_exactly_eight_members(self) -> None:
        # Spec §6.5 enumerates exactly 8 application codes.
        assert len(ChimeraError) == 8

    def test_chimera_error_codes_are_unique(self) -> None:
        codes = [member.value for member in ChimeraError]
        assert len(codes) == len(set(codes))

    def test_chimera_error_codes_all_in_minus_31000_block(self) -> None:
        for member in ChimeraError:
            assert -31007 <= member.value <= -31000


# ---------------------------------------------------------------------------
# ERROR_MESSAGES — default human-readable messages for each code
# ---------------------------------------------------------------------------


class TestErrorMessages:
    """ERROR_MESSAGES gives a default string for every defined code."""

    def test_covers_all_jsonrpc_reserved_codes(self) -> None:
        for code in (
            JSONRPC_PARSE_ERROR,
            JSONRPC_INVALID_REQUEST,
            JSONRPC_METHOD_NOT_FOUND,
            JSONRPC_INVALID_PARAMS,
            JSONRPC_INTERNAL_ERROR,
        ):
            assert code in ERROR_MESSAGES
            assert isinstance(ERROR_MESSAGES[code], str)
            assert len(ERROR_MESSAGES[code]) > 0

    def test_covers_all_chimera_codes(self) -> None:
        for member in ChimeraError:
            assert member.value in ERROR_MESSAGES
            assert isinstance(ERROR_MESSAGES[member.value], str)
            assert len(ERROR_MESSAGES[member.value]) > 0

    def test_no_unexpected_codes(self) -> None:
        # ERROR_MESSAGES must contain ONLY codes we defined — no stragglers.
        expected = {
            JSONRPC_PARSE_ERROR,
            JSONRPC_INVALID_REQUEST,
            JSONRPC_METHOD_NOT_FOUND,
            JSONRPC_INVALID_PARAMS,
            JSONRPC_INTERNAL_ERROR,
        } | {member.value for member in ChimeraError}
        assert set(ERROR_MESSAGES.keys()) == expected


# ---------------------------------------------------------------------------
# RpcError exception class
# ---------------------------------------------------------------------------


class TestRpcError:
    """RpcError carries a JSON-RPC error code, message, and optional data."""

    def test_rpc_error_is_exception(self) -> None:
        assert issubclass(RpcError, Exception)

    def test_can_construct_with_code_only(self) -> None:
        err = RpcError(code=ChimeraError.MODULE_OFFLINE)
        assert err.code == -31000
        # Default message should come from ERROR_MESSAGES.
        assert err.message == ERROR_MESSAGES[-31000]
        assert err.data is None

    def test_can_construct_with_explicit_message(self) -> None:
        err = RpcError(code=ChimeraError.DENIED_BY_POLICY, message="custom reason")
        assert err.code == -31003
        assert err.message == "custom reason"

    def test_can_construct_with_data(self) -> None:
        data = {"reason": "pulse_mode_required_normal"}
        err = RpcError(code=ChimeraError.DENIED_BY_POLICY, data=data)
        assert err.data == data

    def test_accepts_raw_int_code(self) -> None:
        # Code may be a raw int (e.g. one of the JSONRPC_* constants).
        err = RpcError(code=JSONRPC_PARSE_ERROR)
        assert err.code == -32700
        assert err.message == ERROR_MESSAGES[-32700]

    def test_unknown_code_requires_explicit_message(self) -> None:
        # An undefined code with no message provided must raise — silent
        # fallback to "" would hide bugs.
        with pytest.raises(ValueError, match="unknown error code"):
            RpcError(code=-99999)

    def test_unknown_code_accepted_with_explicit_message(self) -> None:
        err = RpcError(code=-99999, message="custom")
        assert err.code == -99999
        assert err.message == "custom"

    def test_str_includes_code_and_message(self) -> None:
        err = RpcError(code=ChimeraError.MODULE_TIMEOUT)
        s = str(err)
        assert "-31001" in s
        assert ERROR_MESSAGES[-31001] in s

    def test_to_dict_returns_jsonrpc_error_object(self) -> None:
        # Per §6.4, the wire form is {"code", "message", "data"} — data omitted if None.
        err = RpcError(
            code=ChimeraError.DENIED_BY_POLICY,
            data={"reason": "fatigue"},
        )
        d = err.to_dict()
        assert d == {
            "code": -31003,
            "message": ERROR_MESSAGES[-31003],
            "data": {"reason": "fatigue"},
        }

    def test_to_dict_omits_data_when_none(self) -> None:
        err = RpcError(code=ChimeraError.FAIL_CLOSED)
        d = err.to_dict()
        assert "data" not in d
        assert d == {"code": -31005, "message": ERROR_MESSAGES[-31005]}
