"""Tests for tokens module (§6.9 capability tokens + §8.6 I6)."""

import base64
import hashlib
import hmac
import inspect
import json
import time

import pytest
from core.errors import ChimeraError, RpcError
from core.tokens import TokenIssuer
from pydantic import ValidationError


def _b64url_decode(s: str) -> bytes:
    """Decode base64url, tolerating omitted padding."""
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


# ---------------------------------------------------------------------------
# Token creation — issue() produces a well-formed token
# ---------------------------------------------------------------------------


class TestTokenCreation:
    """A freshly-issued token has the right shape, fields, and timing."""

    def test_issue_returns_string(self) -> None:
        issuer = TokenIssuer()
        assert isinstance(issuer.issue("CHAFF", ["network.outbound"]), str)

    def test_token_has_two_parts_separated_by_dot(self) -> None:
        issuer = TokenIssuer()
        assert issuer.issue("X", ["cap"]).count(".") == 1

    def test_token_parts_are_base64url(self) -> None:
        issuer = TokenIssuer()
        payload_b64, sig_b64 = issuer.issue("X", ["cap"]).split(".")
        # Must decode without raising — that's the test.
        _b64url_decode(payload_b64)
        _b64url_decode(sig_b64)

    def test_payload_contains_expected_fields(self) -> None:
        issuer = TokenIssuer()
        token = issuer.issue("X", ["cap"])
        payload = json.loads(_b64url_decode(token.split(".")[0]))
        assert {"sub", "caps", "iat", "exp"} <= set(payload.keys())

    def test_issued_at_is_current_unix_time(self) -> None:
        issuer = TokenIssuer()
        before = int(time.time())
        token = issuer.issue("X", ["cap"])
        after = int(time.time())
        payload = json.loads(_b64url_decode(token.split(".")[0]))
        assert before <= payload["iat"] <= after

    def test_expires_at_equals_iat_plus_ttl(self) -> None:
        issuer = TokenIssuer()
        token = issuer.issue("X", ["cap"])  # default TTL 3600
        payload = json.loads(_b64url_decode(token.split(".")[0]))
        assert payload["exp"] == payload["iat"] + 3600

    def test_custom_ttl_respected(self) -> None:
        issuer = TokenIssuer()
        token = issuer.issue("X", [], ttl_s=60)
        payload = json.loads(_b64url_decode(token.split(".")[0]))
        assert payload["exp"] == payload["iat"] + 60

    def test_capabilities_preserved(self) -> None:
        issuer = TokenIssuer()
        token = issuer.issue("X", ["a", "b", "c"])
        payload = json.loads(_b64url_decode(token.split(".")[0]))
        assert payload["caps"] == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# Token validation — accepts the good, rejects everything else
# ---------------------------------------------------------------------------


class TestTokenValidation:
    """validate() returns TokenData on success and raises RpcError otherwise."""

    def test_valid_token_passes_with_correct_capability(self) -> None:
        issuer = TokenIssuer()
        token = issuer.issue("X", ["network.outbound"])
        data = issuer.validate(token, "network.outbound")
        assert data.sub == "X"

    def test_expired_token_raises_not_authorized(self, monkeypatch: pytest.MonkeyPatch) -> None:
        issuer = TokenIssuer()
        monkeypatch.setattr("time.time", lambda: 1_000_000.0)
        token = issuer.issue("X", ["cap"], ttl_s=10)
        monkeypatch.setattr("time.time", lambda: 1_000_100.0)
        with pytest.raises(RpcError) as exc:
            issuer.validate(token, "cap")
        assert exc.value.code == ChimeraError.NOT_AUTHORIZED

    def test_tampered_payload_raises_not_authorized(self) -> None:
        issuer = TokenIssuer()
        payload_b64, sig_b64 = issuer.issue("X", ["cap"]).split(".")
        flipped = ("A" if payload_b64[0] != "A" else "B") + payload_b64[1:]
        with pytest.raises(RpcError) as exc:
            issuer.validate(f"{flipped}.{sig_b64}", "cap")
        assert exc.value.code == ChimeraError.NOT_AUTHORIZED

    def test_tampered_signature_raises_not_authorized(self) -> None:
        issuer = TokenIssuer()
        payload_b64, sig_b64 = issuer.issue("X", ["cap"]).split(".")
        flipped = sig_b64[:-1] + ("A" if sig_b64[-1] != "A" else "B")
        with pytest.raises(RpcError) as exc:
            issuer.validate(f"{payload_b64}.{flipped}", "cap")
        assert exc.value.code == ChimeraError.NOT_AUTHORIZED

    def test_missing_required_capability_raises(self) -> None:
        issuer = TokenIssuer()
        token = issuer.issue("X", ["network.outbound"])
        with pytest.raises(RpcError) as exc:
            issuer.validate(token, "vault.unlock")
        assert exc.value.code == ChimeraError.CAPABILITY_MISSING

    def test_capability_check_is_exact_match(self) -> None:
        # A prefix is not a match — "events" must not satisfy "events.publish".
        issuer = TokenIssuer()
        token = issuer.issue("X", ["events.publish"])
        with pytest.raises(RpcError) as exc:
            issuer.validate(token, "events")
        assert exc.value.code == ChimeraError.CAPABILITY_MISSING

    def test_wrong_signing_key_rejects(self) -> None:
        issuer_a = TokenIssuer()
        issuer_b = TokenIssuer()
        token = issuer_a.issue("X", ["cap"])
        with pytest.raises(RpcError) as exc:
            issuer_b.validate(token, "cap")
        assert exc.value.code == ChimeraError.NOT_AUTHORIZED

    def test_malformed_token_no_dot_raises(self) -> None:
        issuer = TokenIssuer()
        with pytest.raises(RpcError) as exc:
            issuer.validate("notatoken", "any")
        assert exc.value.code == ChimeraError.NOT_AUTHORIZED

    def test_malformed_token_invalid_base64_raises(self) -> None:
        issuer = TokenIssuer()
        with pytest.raises(RpcError) as exc:
            issuer.validate("not!base64.also!bad", "any")
        assert exc.value.code == ChimeraError.NOT_AUTHORIZED

    def test_malformed_payload_not_json_raises(self) -> None:
        # A correctly-signed token whose payload is valid base64 but not JSON
        # must still reject — signature passes, JSON parse fails. Assumes the
        # standard JWT-style scheme: HMAC-SHA256 over the base64url payload bytes.
        issuer = TokenIssuer()
        bad_payload_bytes = b"not valid json {[}"
        payload_b64 = base64.urlsafe_b64encode(bad_payload_bytes).rstrip(b"=").decode()
        sig = hmac.new(issuer._signing_key, payload_b64.encode(), hashlib.sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
        with pytest.raises(RpcError) as exc:
            issuer.validate(f"{payload_b64}.{sig_b64}", "any")
        assert exc.value.code == ChimeraError.NOT_AUTHORIZED

    def test_payload_missing_required_fields_raises(self) -> None:
        # Valid JSON but missing sub/caps/iat/exp must reject with NOT_AUTHORIZED.
        issuer = TokenIssuer()
        bad_payload_bytes = json.dumps({"hello": "world"}).encode()
        payload_b64 = base64.urlsafe_b64encode(bad_payload_bytes).rstrip(b"=").decode()
        sig = hmac.new(issuer._signing_key, payload_b64.encode(), hashlib.sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
        with pytest.raises(RpcError) as exc:
            issuer.validate(f"{payload_b64}.{sig_b64}", "any")
        assert exc.value.code == ChimeraError.NOT_AUTHORIZED


# ---------------------------------------------------------------------------
# TokenData — the decoded payload returned by validate()
# ---------------------------------------------------------------------------


class TestTokenData:
    """The TokenData object is immutable and exposes typed fields."""

    def test_token_data_is_frozen(self) -> None:
        issuer = TokenIssuer()
        data = issuer.validate(issuer.issue("X", ["cap"]), "cap")
        with pytest.raises(ValidationError):
            data.sub = "EVIL"

    def test_token_data_has_correct_subject(self) -> None:
        issuer = TokenIssuer()
        data = issuer.validate(issuer.issue("CHAFF", ["cap"]), "cap")
        assert data.sub == "CHAFF"

    def test_token_data_caps_is_tuple_not_list(self) -> None:
        issuer = TokenIssuer()
        data = issuer.validate(issuer.issue("X", ["a", "b"]), "a")
        assert isinstance(data.caps, tuple)
        assert not isinstance(data.caps, list)

    def test_token_data_iat_exp_are_ints(self) -> None:
        issuer = TokenIssuer()
        data = issuer.validate(issuer.issue("X", ["cap"]), "cap")
        assert isinstance(data.iat, int)
        assert isinstance(data.exp, int)


# ---------------------------------------------------------------------------
# Security properties — constant-time comparison, no key leaks
# ---------------------------------------------------------------------------


class TestSecurityProperties:
    """Cryptographic and operational security guarantees."""

    def test_validate_uses_constant_time_comparison(self) -> None:
        """validate() must use hmac.compare_digest for signature comparison.

        Plain `==` on bytes is non-constant-time: it short-circuits on the first
        differing byte, leaking signature bytes via timing. With timing access
        an attacker can recover the HMAC byte-by-byte. hmac.compare_digest is
        the stdlib's constant-time comparison.

        This is a structural test — it inspects the implementation. If a future
        refactor replaces compare_digest with ==, this catches it before it
        ships. The complement test_tampered_signatures_reject_consistently
        checks the observable behavior.
        """
        source = inspect.getsource(TokenIssuer.validate)
        assert "compare_digest" in source, (
            "validate() must use hmac.compare_digest for signature comparison"
        )

    def test_tampered_signatures_reject_consistently(self) -> None:
        """Tampered signatures must all reject with the same NOT_AUTHORIZED code.

        If validate() leaked WHICH byte was wrong — through distinct error
        codes or distinguishable error paths — an attacker could forge tokens
        incrementally (an oracle attack). Every tampered byte position must
        produce the same observable outcome. This complements
        test_validate_uses_constant_time_comparison: the former inspects the
        implementation; this one verifies the externally-visible behavior.
        """
        issuer = TokenIssuer()
        payload_b64, sig_b64 = issuer.issue("X", ["cap"]).split(".")
        positions = [0, len(sig_b64) // 4, len(sig_b64) // 2, len(sig_b64) - 1]
        for pos in positions:
            original = sig_b64[pos]
            replacement = "A" if original != "A" else "B"
            tampered_sig = sig_b64[:pos] + replacement + sig_b64[pos + 1 :]
            with pytest.raises(RpcError) as exc:
                issuer.validate(f"{payload_b64}.{tampered_sig}", "cap")
            assert exc.value.code == ChimeraError.NOT_AUTHORIZED, (
                f"tamper at signature position {pos} should raise "
                f"NOT_AUTHORIZED, got code {exc.value.code}"
            )

    def test_different_subjects_produce_different_tokens(self) -> None:
        issuer = TokenIssuer()
        assert issuer.issue("A", []) != issuer.issue("B", [])

    def test_same_input_produces_same_token_within_same_second(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Identical inputs at the same iat produce identical tokens.

        Time is mocked so the test is not flaky across second boundaries.
        Determinism here confirms no hidden nonce or randomness in the payload
        — the token is a pure function of (sub, caps, iat, exp, key).
        """
        monkeypatch.setattr("time.time", lambda: 1_700_000_000.0)
        issuer = TokenIssuer()
        assert issuer.issue("A", ["x"]) == issuer.issue("A", ["x"])

    def test_str_repr_does_not_leak_signing_key(self) -> None:
        """str() and repr() of an issuer must never include the signing key.

        A leak would put the key into log files, exception tracebacks, and
        REPL output. Default Python repr does not expose attributes; this is
        a preventative test against a future custom __repr__ that includes
        fields.
        """
        issuer = TokenIssuer()
        key_hex = issuer._signing_key.hex()
        assert key_hex not in str(issuer)
        assert key_hex not in repr(issuer)


# ---------------------------------------------------------------------------
# TokenIssuer — instance properties of the issuer itself
# ---------------------------------------------------------------------------


class TestTokenIssuer:
    """The issuer holds a fresh in-RAM signing key per instance."""

    def test_init_generates_signing_key(self) -> None:
        issuer = TokenIssuer()
        assert isinstance(issuer._signing_key, bytes)
        assert len(issuer._signing_key) == 32

    def test_different_issuers_have_different_keys(self) -> None:
        assert TokenIssuer()._signing_key != TokenIssuer()._signing_key

    def test_issuer_cannot_validate_other_issuers_tokens(self) -> None:
        issuer_a = TokenIssuer()
        issuer_b = TokenIssuer()
        token = issuer_a.issue("X", ["cap"])
        with pytest.raises(RpcError) as exc:
            issuer_b.validate(token, "cap")
        assert exc.value.code == ChimeraError.NOT_AUTHORIZED


# ---------------------------------------------------------------------------
# Edge cases — empty caps, dotted names, long subjects, unicode
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases that often hide bugs in token systems."""

    def test_empty_capabilities_list_token_always_fails_validation(self) -> None:
        issuer = TokenIssuer()
        token = issuer.issue("X", [])
        with pytest.raises(RpcError) as exc:
            issuer.validate(token, "anything")
        assert exc.value.code == ChimeraError.CAPABILITY_MISSING

    def test_capability_with_dots_works(self) -> None:
        issuer = TokenIssuer()
        data = issuer.validate(issuer.issue("X", ["events.publish"]), "events.publish")
        assert "events.publish" in data.caps

    def test_very_long_subject_works(self) -> None:
        issuer = TokenIssuer()
        long_subject = "X" * 1000
        data = issuer.validate(issuer.issue(long_subject, ["cap"]), "cap")
        assert data.sub == long_subject

    def test_unicode_subject_works(self) -> None:
        issuer = TokenIssuer()
        subject = "CHAFF-моdule"
        data = issuer.validate(issuer.issue(subject, ["cap"]), "cap")
        assert data.sub == subject
