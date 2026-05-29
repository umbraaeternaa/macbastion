"""Tests for envelope module (§6.4 — JSON-RPC 2.0 wire format)."""

import pytest
from core.envelope import (
    Notification,
    Request,
    Response,
    parse,
    parse_frame,
    serialize,
    serialize_frame,
)
from core.errors import ChimeraError, RpcError
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Request parsing
# ---------------------------------------------------------------------------


class TestRequestParse:
    """A Request carries jsonrpc, id, method, and optional params."""

    def test_parses_valid_request_with_int_id(self) -> None:
        msg = parse('{"jsonrpc":"2.0","id":42,"method":"core.register","params":{"name":"chaff"}}')
        assert isinstance(msg, Request)
        assert msg.id == 42
        assert msg.method == "core.register"
        assert msg.params == {"name": "chaff"}

    def test_parses_valid_request_with_string_id(self) -> None:
        msg = parse('{"jsonrpc":"2.0","id":"req-abc","method":"core.register"}')
        assert isinstance(msg, Request)
        assert msg.id == "req-abc"

    def test_parses_request_without_params(self) -> None:
        msg = parse('{"jsonrpc":"2.0","id":1,"method":"core.ping"}')
        assert isinstance(msg, Request)
        assert msg.params is None

    def test_rejects_request_missing_jsonrpc(self) -> None:
        with pytest.raises(ValidationError):
            parse('{"id":1,"method":"core.ping"}')

    def test_rejects_request_wrong_jsonrpc_version(self) -> None:
        with pytest.raises(ValidationError):
            parse('{"jsonrpc":"1.0","id":1,"method":"core.ping"}')

    def test_rejects_request_missing_method(self) -> None:
        with pytest.raises(ValidationError):
            parse('{"jsonrpc":"2.0","id":1}')


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


class TestResponseParse:
    """A Response carries jsonrpc, id, and exactly one of result/error."""

    def test_parses_success_response(self) -> None:
        msg = parse('{"jsonrpc":"2.0","id":42,"result":{"ok":true}}')
        assert isinstance(msg, Response)
        assert msg.result == {"ok": True}
        assert msg.error is None

    def test_parses_error_response(self) -> None:
        msg = parse('{"jsonrpc":"2.0","id":42,"error":{"code":-31003,"message":"denied"}}')
        assert isinstance(msg, Response)
        assert msg.error == {"code": -31003, "message": "denied"}
        assert msg.result is None

    def test_response_with_null_id_allowed(self) -> None:
        # Per JSON-RPC, a parse-error response may carry a null id.
        msg = parse('{"jsonrpc":"2.0","id":null,"result":{"ok":true}}')
        assert isinstance(msg, Response)
        assert msg.id is None

    def test_rejects_response_with_both_result_and_error(self) -> None:
        with pytest.raises(ValidationError):
            Response(
                jsonrpc="2.0",
                id=42,
                result={"ok": True},
                error={"code": -31000, "message": "x"},
            )

    def test_rejects_response_with_neither_result_nor_error(self) -> None:
        with pytest.raises(ValidationError):
            Response(jsonrpc="2.0", id=42)

    def test_response_error_field_accepts_rpcerror_dict(self) -> None:
        msg = parse('{"jsonrpc":"2.0","id":1,"error":{"code":-31000,"message":"module offline"}}')
        assert isinstance(msg, Response)
        assert msg.error == {"code": -31000, "message": "module offline"}


# ---------------------------------------------------------------------------
# Notification parsing
# ---------------------------------------------------------------------------


class TestNotificationParse:
    """A Notification carries jsonrpc, method, optional params — and no id."""

    def test_parses_valid_notification(self) -> None:
        msg = parse('{"jsonrpc":"2.0","method":"module.heartbeat","params":{"seq":1}}')
        assert isinstance(msg, Notification)
        assert msg.method == "module.heartbeat"
        assert msg.params == {"seq": 1}

    def test_notification_without_params(self) -> None:
        msg = parse('{"jsonrpc":"2.0","method":"module.ping"}')
        assert isinstance(msg, Notification)
        assert msg.params is None

    def test_rejects_notification_with_id_field(self) -> None:
        # An id present means this is a Request, not a Notification.
        msg = parse('{"jsonrpc":"2.0","id":1,"method":"module.heartbeat","params":{"seq":1}}')
        assert isinstance(msg, Request)


# ---------------------------------------------------------------------------
# parse() dispatch — Request vs Notification vs Response by field presence
# ---------------------------------------------------------------------------


class TestParseDispatch:
    """The parse() function decides the message type by field presence."""

    def test_parse_request_when_id_and_method_present(self) -> None:
        msg = parse('{"jsonrpc":"2.0","id":1,"method":"core.register"}')
        assert isinstance(msg, Request)

    def test_parse_notification_when_method_but_no_id(self) -> None:
        msg = parse('{"jsonrpc":"2.0","method":"core.register"}')
        assert isinstance(msg, Notification)

    def test_parse_response_when_id_and_result_present(self) -> None:
        msg = parse('{"jsonrpc":"2.0","id":1,"result":{"ok":true}}')
        assert isinstance(msg, Response)

    def test_parse_response_when_id_and_error_present(self) -> None:
        msg = parse('{"jsonrpc":"2.0","id":1,"error":{"code":-31000,"message":"x"}}')
        assert isinstance(msg, Response)

    def test_parse_rejects_ambiguous_message(self) -> None:
        # method + result together mixes request and response shapes.
        with pytest.raises(ValidationError):
            parse('{"jsonrpc":"2.0","id":1,"method":"core.register","result":{"ok":true}}')


# ---------------------------------------------------------------------------
# id types — int or str only (decision 3A: no floats)
# ---------------------------------------------------------------------------


class TestIdTypes:
    """A message id is an int or a str — never a float, dict, or list."""

    def test_id_can_be_int(self) -> None:
        msg = parse('{"jsonrpc":"2.0","id":42,"method":"core.ping"}')
        assert isinstance(msg, Request)
        assert msg.id == 42

    def test_id_can_be_str(self) -> None:
        msg = parse('{"jsonrpc":"2.0","id":"abc-123","method":"core.ping"}')
        assert isinstance(msg, Request)
        assert msg.id == "abc-123"

    def test_id_cannot_be_float(self) -> None:
        with pytest.raises(ValidationError):
            parse('{"jsonrpc":"2.0","id":42.5,"method":"core.ping"}')

    def test_id_cannot_be_dict(self) -> None:
        with pytest.raises(ValidationError):
            parse('{"jsonrpc":"2.0","id":{"x":1},"method":"core.ping"}')

    def test_id_cannot_be_list(self) -> None:
        with pytest.raises(ValidationError):
            parse('{"jsonrpc":"2.0","id":[1,2],"method":"core.ping"}')


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestSerialize:
    """serialize() produces a single-line JSON string; parse() reverses it."""

    def test_serialize_request_round_trip(self) -> None:
        req = Request(jsonrpc="2.0", id=42, method="core.register", params={"name": "chaff"})
        assert parse(serialize(req)) == req

    def test_serialize_response_round_trip(self) -> None:
        resp = Response(jsonrpc="2.0", id=42, result={"ok": True})
        assert parse(serialize(resp)) == resp

    def test_serialize_notification_round_trip(self) -> None:
        note = Notification(jsonrpc="2.0", method="module.heartbeat", params={"seq": 1})
        assert parse(serialize(note)) == note

    def test_serialize_produces_single_line(self) -> None:
        req = Request(jsonrpc="2.0", id=1, method="core.ping")
        assert "\n" not in serialize(req)

    def test_serialize_includes_jsonrpc_field(self) -> None:
        req = Request(jsonrpc="2.0", id=1, method="core.ping")
        assert '"jsonrpc":"2.0"' in serialize(req)

    def test_serialize_omits_none_fields(self) -> None:
        req = Request(jsonrpc="2.0", id=1, method="core.ping")
        assert "params" not in serialize(req)


# ---------------------------------------------------------------------------
# NDJSON framing
# ---------------------------------------------------------------------------


class TestNdjsonFraming:
    """Frames are newline-terminated; parse_frame() tolerates a missing one."""

    def test_serialize_frame_ends_with_newline(self) -> None:
        req = Request(jsonrpc="2.0", id=1, method="core.ping")
        assert serialize_frame(req).endswith("\n")

    def test_serialize_frame_contains_only_one_newline(self) -> None:
        req = Request(jsonrpc="2.0", id=1, method="core.ping")
        assert serialize_frame(req).count("\n") == 1

    def test_parse_frame_strips_trailing_newline(self) -> None:
        line = '{"jsonrpc":"2.0","id":1,"method":"core.ping"}'
        assert parse_frame(line + "\n") == parse(line)

    def test_parse_frame_handles_no_trailing_newline(self) -> None:
        msg = parse_frame('{"jsonrpc":"2.0","id":1,"method":"core.ping"}')
        assert isinstance(msg, Request)

    def test_parse_frame_rejects_empty_line(self) -> None:
        with pytest.raises(ValueError):
            parse_frame("")

    def test_parse_frame_rejects_whitespace_only(self) -> None:
        with pytest.raises(ValueError):
            parse_frame("   \n")


# ---------------------------------------------------------------------------
# Batch rejection — not supported in v0.2.0 (decision 4A)
# ---------------------------------------------------------------------------


class TestBatchRejection:
    """JSON-RPC batches (top-level arrays) are explicitly rejected."""

    def test_parse_rejects_json_array(self) -> None:
        with pytest.raises(ValueError, match="batch not supported"):
            parse('[{"jsonrpc":"2.0","id":1,"method":"a"},{"jsonrpc":"2.0","id":2,"method":"b"}]')

    def test_parse_rejects_empty_array(self) -> None:
        with pytest.raises(ValueError, match="batch not supported"):
            parse("[]")


# ---------------------------------------------------------------------------
# Error integration — Response.error accepts RpcError.to_dict() output
# ---------------------------------------------------------------------------


class TestErrorIntegration:
    """Response.error must accept the dict produced by RpcError.to_dict()."""

    def test_response_accepts_rpcerror_to_dict(self) -> None:
        err = RpcError(code=ChimeraError.DENIED_BY_POLICY, data={"reason": "x"})
        error_dict = err.to_dict()
        resp = Response(jsonrpc="2.0", id=1, error=error_dict)
        assert resp.error == error_dict

    def test_response_error_can_be_serialized_back(self) -> None:
        err = RpcError(code=ChimeraError.DENIED_BY_POLICY, data={"reason": "x"})
        resp = Response(jsonrpc="2.0", id=1, error=err.to_dict())
        assert parse(serialize(resp)) == resp
