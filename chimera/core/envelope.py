"""JSON-RPC 2.0 wire format (§6.4)."""

import json
from typing import Any, Literal, Self, TypeAlias

from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr, model_validator


class Request(BaseModel):
    """A method call expecting a response (§6.4)."""

    model_config = ConfigDict(extra="forbid")

    jsonrpc: Literal["2.0"]
    id: StrictInt | StrictStr
    method: str
    params: dict[str, Any] | list[Any] | None = None


class Response(BaseModel):
    """A reply to a Request — exactly one of result or error (§6.4)."""

    model_config = ConfigDict(extra="forbid")

    jsonrpc: Literal["2.0"]
    id: StrictInt | StrictStr | None
    result: Any = None
    error: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _exactly_one_of_result_or_error(self) -> Self:
        if (self.result is None) == (self.error is None):
            raise ValueError("response must have exactly one of result or error")
        return self


class Notification(BaseModel):
    """A fire-and-forget event — no id, no response (§6.4)."""

    model_config = ConfigDict(extra="forbid")

    jsonrpc: Literal["2.0"]
    method: str
    params: dict[str, Any] | list[Any] | None = None


Message: TypeAlias = Request | Response | Notification


def parse(data: str) -> Message:
    """Parse a single JSON line into the matching message type.

    Raises ValueError on a JSON array (batches unsupported, decision 4A) and
    pydantic.ValidationError on a malformed message.
    """
    obj: Any = json.loads(data)
    if isinstance(obj, list):
        raise ValueError("batch not supported")
    if not isinstance(obj, dict):
        raise ValueError("message must be a JSON object")
    has_id = "id" in obj
    has_method = "method" in obj
    has_payload = "result" in obj or "error" in obj
    if has_payload and not has_method:
        return Response.model_validate(obj)
    if has_method and has_id and not has_payload:
        return Request.model_validate(obj)
    if has_method and not has_id and not has_payload:
        return Notification.model_validate(obj)
    # Shape mixing, a missing method, or otherwise malformed: validating as a
    # Request surfaces a precise ValidationError (extra fields are forbidden).
    return Request.model_validate(obj)


def serialize(msg: Message) -> str:
    """Serialize a message to a compact single-line JSON string."""
    return msg.model_dump_json(exclude_none=True)


def parse_frame(line: str) -> Message:
    """Parse one NDJSON frame, tolerating a missing trailing newline.

    Raises ValueError on an empty or whitespace-only line.
    """
    frame = line.rstrip("\n")
    if not frame.strip():
        raise ValueError("empty frame")
    return parse(frame)


def serialize_frame(msg: Message) -> str:
    """Serialize a message to an NDJSON frame (JSON + newline terminator)."""
    return serialize(msg) + "\n"
