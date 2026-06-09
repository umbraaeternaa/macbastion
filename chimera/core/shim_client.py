"""Core's client to the privileged shim (§7.10 / §8.8) — RED stub.

The unprivileged core reaches the root shim over its UNIX socket
(/var/run/chimera-shim.sock) and asks for one of the four enumerated ops. This is the
ONLY path core has into root; auth is the shim's: peercred for ping/lock, plus a per-boot
secret (obtained via shim.handshake, issued only to a code-sig-attested peer) for the
destructive ops evict/reboot/killall.
"""

from __future__ import annotations

import asyncio
import contextlib
import json

DEFAULT_SHIM_SOCKET = "/var/run/chimera-shim.sock"


class ShimError(Exception):
    """A shim error response, or an unreachable/closed shim channel."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(f"shim error {code}: {message}")
        self.code = code
        self.message = message


class ShimClient:
    """One-shot JSON-RPC client to the privileged shim (a fresh connection per call)."""

    def __init__(self, socket_path: str = DEFAULT_SHIM_SOCKET, timeout: float = 5.0) -> None:
        self._path = str(socket_path)
        self._timeout = timeout
        self._id = 0
        self._secret: str | None = None  # per-boot secret, obtained lazily via shim.handshake

    async def call(self, method: str, params: dict[str, object] | None = None) -> dict[str, object]:
        """Send one shim.* request; return its `result`, or raise ShimError."""
        self._id += 1
        req: dict[str, object] = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            req["params"] = params
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(self._path), self._timeout
            )
        except (OSError, TimeoutError) as exc:
            raise ShimError(-32000, f"cannot reach shim at {self._path}: {exc}") from exc
        try:
            writer.write((json.dumps(req) + "\n").encode())
            await writer.drain()
            raw = await asyncio.wait_for(reader.readline(), self._timeout)
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
        if not raw:
            raise ShimError(-32000, "shim closed the connection without responding")
        msg = json.loads(raw.decode())
        err = msg.get("error")
        if err is not None:
            raise ShimError(int(err.get("code", -32000)), str(err.get("message", "")))
        result = msg.get("result", {})
        return result if isinstance(result, dict) else {}

    async def handshake(self) -> str:
        """Obtain the per-boot secret from the shim (issued only to an attested peer)."""
        result = await self.call("shim.handshake")
        secret = result.get("secret")
        if not isinstance(secret, str):
            raise ShimError(-32000, "shim.handshake returned no secret")
        self._secret = secret
        return secret

    async def _ensure_secret(self) -> str:
        """The cached per-boot secret, handshaking once on first need."""
        secret = self._secret
        if secret is None:
            secret = await self.handshake()
        return secret

    async def ping(self) -> dict[str, object]:
        return await self.call("shim.ping")

    async def lock(self) -> dict[str, object]:
        return await self.call("shim.lock")

    async def evict(self) -> dict[str, object]:
        return await self.call("shim.evict", {"secret": await self._ensure_secret()})

    async def reboot(self) -> dict[str, object]:
        return await self.call("shim.reboot", {"secret": await self._ensure_secret()})

    async def killall(self) -> dict[str, object]:
        return await self.call("shim.killall", {"secret": await self._ensure_secret()})
