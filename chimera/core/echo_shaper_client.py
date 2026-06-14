"""Core's client to the ECHO packet-shaper (§8 Amendment A1, EP-5/EP-10).

The unprivileged core reaches the SEPARATE root echo-shaper daemon over its UNIX socket
(/var/run/chimera-echo-shaper.sock) to turn ECHO's constant-rate dummynet shaping on/off. Auth
is the shaper's: peercred for ping/handshake, plus a per-boot secret (obtained via
shaper.handshake — peercred-only, EP-10) presented on the pf ops. Mirrors core/shim_client.py.
"""

from __future__ import annotations

import asyncio
import contextlib
import json

DEFAULT_SHAPER_SOCKET = "/var/run/chimera-echo-shaper.sock"


class EchoShaperError(Exception):
    """An echo-shaper error response, or an unreachable/closed shaper channel."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(f"echo-shaper error {code}: {message}")
        self.code = code
        self.message = message


class EchoShaperClient:
    """One-shot JSON-RPC client to the root echo-shaper (a fresh connection per call)."""

    def __init__(self, socket_path: str = DEFAULT_SHAPER_SOCKET, timeout: float = 5.0) -> None:
        self._path = str(socket_path)
        self._timeout = timeout
        self._id = 0
        self._secret: str | None = None  # per-boot secret, obtained lazily via shaper.handshake

    async def call(self, method: str, params: dict[str, object] | None = None) -> dict[str, object]:
        """Send one shaper.* request; return its `result`, or raise EchoShaperError."""
        self._id += 1
        req: dict[str, object] = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            req["params"] = params
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(self._path), self._timeout
            )
        except (OSError, TimeoutError) as exc:
            raise EchoShaperError(
                -32000, f"cannot reach echo-shaper at {self._path}: {exc}"
            ) from exc
        try:
            writer.write((json.dumps(req) + "\n").encode())
            await writer.drain()
            raw = await asyncio.wait_for(reader.readline(), self._timeout)
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
        if not raw:
            raise EchoShaperError(-32000, "echo-shaper closed the connection without responding")
        msg = json.loads(raw.decode())
        err = msg.get("error")
        if err is not None:
            raise EchoShaperError(int(err.get("code", -32000)), str(err.get("message", "")))
        result = msg.get("result", {})
        return result if isinstance(result, dict) else {}

    async def handshake(self) -> str:
        """Obtain the per-boot secret from the shaper (peercred-only, EP-10) and cache it."""
        result = await self.call("shaper.handshake")
        secret = result.get("secret")
        if not isinstance(secret, str):
            raise EchoShaperError(-32000, "shaper.handshake returned no secret")
        self._secret = secret
        return secret

    async def _ensure_secret(self) -> str:
        """The cached per-boot secret, handshaking once on first need."""
        secret = self._secret
        if secret is None:
            secret = await self.handshake()
        return secret

    async def ping(self) -> dict[str, object]:
        return await self.call("shaper.ping")

    async def shape(self, rate_kbps: int) -> dict[str, object]:
        """Turn ECHO shaping ON at rate_kbps — load the dummynet anchor (both directions)."""
        return await self.call(
            "shaper.anchor.load",
            {"rate_kbps": int(rate_kbps), "secret": await self._ensure_secret()},
        )

    async def unshape(self) -> dict[str, object]:
        """Turn ECHO shaping OFF — remove the anchor, restore normal flow (FAIL-OPEN)."""
        return await self.call("shaper.anchor.remove", {"secret": await self._ensure_secret()})
