"""CHIMERA error codes (§6.5)."""

from enum import IntEnum
from typing import Final

# JSON-RPC 2.0 reserved codes (used as-is).
JSONRPC_PARSE_ERROR: Final[int] = -32700
JSONRPC_INVALID_REQUEST: Final[int] = -32600
JSONRPC_METHOD_NOT_FOUND: Final[int] = -32601
JSONRPC_INVALID_PARAMS: Final[int] = -32602
JSONRPC_INTERNAL_ERROR: Final[int] = -32603


class ChimeraError(IntEnum):
    """CHIMERA application error codes (the -31000 block)."""

    MODULE_OFFLINE = -31000
    MODULE_TIMEOUT = -31001
    CAPABILITY_MISSING = -31002
    DENIED_BY_POLICY = -31003
    PRECONDITION_FAILED = -31004
    FAIL_CLOSED = -31005
    RATE_LIMITED = -31006
    NOT_AUTHORIZED = -31007


ERROR_MESSAGES: Final[dict[int, str]] = {
    JSONRPC_PARSE_ERROR: "parse error",
    JSONRPC_INVALID_REQUEST: "invalid request",
    JSONRPC_METHOD_NOT_FOUND: "method not found",
    JSONRPC_INVALID_PARAMS: "invalid params",
    JSONRPC_INTERNAL_ERROR: "internal error",
    ChimeraError.MODULE_OFFLINE: "module offline",
    ChimeraError.MODULE_TIMEOUT: "module timeout",
    ChimeraError.CAPABILITY_MISSING: "capability missing",
    ChimeraError.DENIED_BY_POLICY: "denied by policy",
    ChimeraError.PRECONDITION_FAILED: "precondition failed",
    ChimeraError.FAIL_CLOSED: "fail-closed",
    ChimeraError.RATE_LIMITED: "rate limited",
    ChimeraError.NOT_AUTHORIZED: "not authorized",
}


class RpcError(Exception):
    """A JSON-RPC error: numeric code, message, and optional data (§6.4)."""

    def __init__(
        self,
        code: int,
        message: str | None = None,
        data: object | None = None,
    ) -> None:
        if message is None:
            if code not in ERROR_MESSAGES:
                raise ValueError(f"unknown error code: {code}")
            message = ERROR_MESSAGES[code]
        self.code = int(code)
        self.message = message
        self.data = data
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"code": self.code, "message": self.message}
        if self.data is not None:
            result["data"] = self.data
        return result
