"""Capability token issuer (§6.9, §8.6 I6)."""

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from core.errors import ChimeraError, RpcError


def _b64url_decode(s: str) -> bytes:
    """Decode base64url, tolerating omitted padding (JWT convention strips it)."""
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class TokenData(BaseModel):
    """Decoded capability-token payload (immutable)."""

    model_config = ConfigDict(frozen=True)

    sub: str
    caps: tuple[str, ...]
    iat: int
    exp: int


class TokenIssuer:
    """Issues and validates HMAC-SHA256 capability tokens.

    Stateless: tokens are self-contained. The signing key is in-RAM only,
    generated at init. A core restart yields a new key and invalidates every
    outstanding token — by design (§8.6 I6: no runtime scope escalation).
    """

    DEFAULT_TTL_S: ClassVar[int] = 3600

    def __init__(self) -> None:
        self._signing_key: bytes = secrets.token_bytes(32)

    def issue(
        self,
        subject: str,
        capabilities: list[str],
        ttl_s: int | None = None,
    ) -> str:
        """Issue a fresh token. Returns 'base64url(payload).base64url(signature)'."""
        ttl = self.DEFAULT_TTL_S if ttl_s is None else ttl_s
        iat = int(time.time())
        exp = iat + ttl
        payload = {"sub": subject, "caps": capabilities, "iat": iat, "exp": exp}
        payload_json = json.dumps(payload, separators=(",", ":"))
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).rstrip(b"=").decode()
        sig = hmac.new(self._signing_key, payload_b64.encode(), hashlib.sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
        return f"{payload_b64}.{sig_b64}"

    def validate(self, token: str, required_capability: str) -> TokenData:
        """Verify signature and expiry, check capability, return TokenData.

        Raises RpcError(NOT_AUTHORIZED) on any signature, format, or expiry
        failure. Raises RpcError(CAPABILITY_MISSING) when the token is valid
        but does not carry the required capability.
        """
        # Split — exactly two parts on the single '.'
        try:
            payload_b64, sig_b64 = token.split(".")
        except ValueError as e:
            raise RpcError(code=ChimeraError.NOT_AUTHORIZED) from e

        # Constant-time signature comparison in canonical base64url form
        # (Trap 1: == on bytes is non-constant-time and leaks bytes via timing).
        # Comparing canonical b64url strings — not decoded bytes — also rejects
        # non-canonical encodings (e.g., padding-bit variants that decode to
        # the same bytes), which would otherwise pass byte-comparison.
        expected = hmac.new(self._signing_key, payload_b64.encode(), hashlib.sha256).digest()
        expected_b64 = base64.urlsafe_b64encode(expected).rstrip(b"=").decode()
        if not hmac.compare_digest(expected_b64.encode(), sig_b64.encode()):
            raise RpcError(code=ChimeraError.NOT_AUTHORIZED)

        # Decode and parse the payload.
        try:
            payload_bytes = _b64url_decode(payload_b64)
            payload = json.loads(payload_bytes)
        except ValueError as e:
            raise RpcError(code=ChimeraError.NOT_AUTHORIZED) from e

        # Trust nothing from untrusted JSON (Trap 3): type-check every field.
        if not isinstance(payload, dict):
            raise RpcError(code=ChimeraError.NOT_AUTHORIZED)
        sub = payload.get("sub")
        caps = payload.get("caps")
        iat = payload.get("iat")
        exp = payload.get("exp")
        if not isinstance(sub, str):
            raise RpcError(code=ChimeraError.NOT_AUTHORIZED)
        if not isinstance(caps, list) or not all(isinstance(c, str) for c in caps):
            raise RpcError(code=ChimeraError.NOT_AUTHORIZED)
        if not isinstance(iat, int) or isinstance(iat, bool):
            raise RpcError(code=ChimeraError.NOT_AUTHORIZED)
        if not isinstance(exp, int) or isinstance(exp, bool):
            raise RpcError(code=ChimeraError.NOT_AUTHORIZED)

        if time.time() >= exp:
            raise RpcError(code=ChimeraError.NOT_AUTHORIZED)

        if required_capability not in caps:
            raise RpcError(code=ChimeraError.CAPABILITY_MISSING)

        return TokenData(sub=sub, caps=tuple(caps), iat=iat, exp=exp)
