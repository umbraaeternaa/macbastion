"""Tests for server module (§6.3 transport + §6.2 hub + §6.9 auth).

RED phase: defines the contract for core/server.py before it exists. Server
is the integrator — it composes registry + lifecycle + broker + tokens +
envelope into the core hub (§6.2).

Decisions pinned here (operator-approved, all 10 + sub-decisions):
- D1 two UNIX sockets: core.sock (commands) + events.sock (events), §6.3.
- D2 one long-lived connection per peer.
- D3 register-implies-module: a connection starts surface-scoped (full); the
  first core.register reissues its token module-scoped (sub=name).
- D4 core.* ONLY in v0.2.0; any module.method -> -31000 module offline
  (no routing yet — honest MVP, MANIFESTO §4).
- D5 centralized error mapping (Python exception -> JSON-RPC error, §6.5).
- D6 subscribe-on-demand (core.subscribe).
- D7 one asyncio task per connection; no connection cap.
- D8 graceful shutdown: stop-accept, close, unlink sockets.
- D9 hybrid tests: handle_command() unit-tested without sockets + a few
  real-socket integration tests in tmp_path.
- D10 start()/stop() + async context manager.

API surface (operator-confirmed):
- Server(config, registry, lifecycle, broker, token_issuer)
- Server.new_connection() -> Connection (issues surface/full token)
- async Server.handle_command(request, conn) -> Response  (dispatch entry)
- async Server.start()/stop(); async with Server(...)
- core.status returns the extended payload {core:{version,uptime_seconds},
  modules:{<name>:{version,status,methods,events,last_seen,restart_count}}}.

Token note (4B): scope has no teeth yet (no module methods to forbid). Token
is validated only for core.* methods; a module method short-circuits to
-31000 before any auth check. A forged token on a core.* method -> -31007.
"""

import asyncio
import os
import stat
from typing import Any

import pytest
from core.broker import EventBroker
from core.config import CoreConfig
from core.envelope import Request, Response, parse
from core.lifecycle import Lifecycle
from core.registry import Registry
from core.server import Connection, Server
from core.tokens import TokenIssuer

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class FakeClock:
    """Monotonic clock advanced by hand — used for Lifecycle only."""

    def __init__(self, start: float = 1000.0) -> None:
        self._t = start

    def now(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def _make_server(tmp_path: Any) -> Server:
    """Full DI wiring with sockets under tmp_path. TokenIssuer uses real time
    (TTL is 3600s; tests run in milliseconds)."""
    config = CoreConfig.model_validate({"socket_dir": str(tmp_path)})
    broker = EventBroker()
    lifecycle = Lifecycle(config, broker, clock=FakeClock().now)
    registry = Registry(lifecycle, broker)
    token_issuer = TokenIssuer()
    return Server(config, registry, lifecycle, broker, token_issuer)


def _req(method: str, req_id: int = 1, **params: Any) -> Request:
    """Build a JSON-RPC Request (params omitted when empty)."""
    return Request(jsonrpc="2.0", id=req_id, method=method, params=params or None)


async def _register(
    server: Server,
    conn: Connection,
    name: str = "vault",
    version: str = "1.0",
    methods: list[str] | None = None,
    events: list[str] | None = None,
    depends_on: list[str] | None = None,
) -> Response:
    return await server.handle_command(
        _req(
            "core.register",
            module=name,
            version=version,
            methods=methods if methods is not None else ["vault.unlock"],
            events=events if events is not None else [],
            depends_on=depends_on if depends_on is not None else [],
        ),
        conn,
    )


async def _roundtrip(sock_path: Any, line: str, timeout: float = 2.0) -> Response:
    """Open a UNIX connection, send one NDJSON frame, read one response frame."""
    reader, writer = await asyncio.open_unix_connection(str(sock_path))
    try:
        writer.write(line.encode())
        await writer.drain()
        raw = await asyncio.wait_for(reader.readline(), timeout=timeout)
        return parse(raw.decode())
    finally:
        writer.close()
        await writer.wait_closed()


def _mode(path: Any) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)


# ---------------------------------------------------------------------------
# Socket creation — bind, permissions
# ---------------------------------------------------------------------------


class TestSocketCreation:
    """start() binds both sockets with the §6.3 permissions."""

    async def test_both_sockets_created(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        await server.start()
        try:
            assert (tmp_path / "core.sock").exists()
            assert (tmp_path / "events.sock").exists()
        finally:
            await server.stop()

    async def test_core_socket_mode_0600(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        await server.start()
        try:
            assert _mode(tmp_path / "core.sock") == 0o600
        finally:
            await server.stop()

    async def test_events_socket_mode_0600(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        await server.start()
        try:
            assert _mode(tmp_path / "events.sock") == 0o600
        finally:
            await server.stop()

    async def test_socket_dir_mode_0700(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        await server.start()
        try:
            assert _mode(tmp_path) == 0o700
        finally:
            await server.stop()


# ---------------------------------------------------------------------------
# Connect — token issuance, default surface scope (D3)
# ---------------------------------------------------------------------------


class TestConnect:
    """new_connection() issues a surface-scoped (full) token."""

    def test_returns_connection(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        assert isinstance(server.new_connection(), Connection)

    def test_default_subject_is_surface(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        assert server.new_connection().subject == "surface"

    def test_default_is_not_module(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        assert server.new_connection().is_module is False

    def test_issues_nonempty_token(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        assert server.new_connection().token


# ---------------------------------------------------------------------------
# Register — 3B: core.register reissues token module-scoped
# ---------------------------------------------------------------------------


class TestRegister:
    """The first core.register turns a surface connection into a module."""

    async def test_register_marks_connection_module(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        await _register(server, conn, name="vault")
        assert conn.is_module is True

    async def test_register_sets_subject_to_module_name(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        await _register(server, conn, name="vault")
        assert conn.subject == "vault"

    async def test_register_reissues_token(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        before = conn.token
        await _register(server, conn, name="vault")
        assert conn.token != before

    async def test_register_returns_ok(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        resp = await _register(server, conn, name="vault")
        assert resp.error is None


# ---------------------------------------------------------------------------
# core.register handler — delegates to registry
# ---------------------------------------------------------------------------


class TestCoreRegister:
    """core.register delegates to registry.register."""

    async def test_module_appears_in_capabilities(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        await _register(server, conn, name="vault")
        caps = await server.handle_command(_req("core.capabilities"), conn)
        assert "vault" in caps.result

    async def test_version_recorded(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        await _register(server, conn, name="vault", version="0.7.0")
        caps = await server.handle_command(_req("core.capabilities"), conn)
        assert caps.result["vault"]["version"] == "0.7.0"

    async def test_reregister_overwrites_version(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        await _register(server, conn, name="vault", version="1.0")
        await _register(server, conn, name="vault", version="2.0")
        caps = await server.handle_command(_req("core.capabilities"), conn)
        assert caps.result["vault"]["version"] == "2.0"


# ---------------------------------------------------------------------------
# core.heartbeat handler — delegates to lifecycle
# ---------------------------------------------------------------------------


class TestCoreHeartbeat:
    """core.heartbeat delegates to lifecycle.heartbeat."""

    async def test_heartbeat_returns_ok(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        await _register(server, conn, name="vault")
        resp = await server.handle_command(
            _req("core.heartbeat", module="vault"), conn
        )
        assert resp.error is None

    async def test_heartbeat_sets_last_seen(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        await _register(server, conn, name="vault")
        await server.handle_command(_req("core.heartbeat", module="vault"), conn)
        status = await server.handle_command(_req("core.status"), conn)
        assert status.result["modules"]["vault"]["last_seen"] == 1000.0

    async def test_heartbeat_unknown_module_errors(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        resp = await server.handle_command(
            _req("core.heartbeat", module="ghost"), conn
        )
        assert resp.error is not None and resp.error["code"] == -31000


# ---------------------------------------------------------------------------
# core.deregister handler — delegates to registry
# ---------------------------------------------------------------------------


class TestCoreDeregister:
    """core.deregister delegates to registry.deregister."""

    async def test_deregister_returns_ok(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        await _register(server, conn, name="vault")
        resp = await server.handle_command(
            _req("core.deregister", module="vault"), conn
        )
        assert resp.error is None

    async def test_deregister_removes_from_capabilities(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        await _register(server, conn, name="vault")
        await server.handle_command(_req("core.deregister", module="vault"), conn)
        caps = await server.handle_command(_req("core.capabilities"), conn)
        assert "vault" not in caps.result

    async def test_deregister_unknown_is_ok(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        resp = await server.handle_command(
            _req("core.deregister", module="ghost"), conn
        )
        assert resp.error is None  # idempotent no-op


# ---------------------------------------------------------------------------
# core.capabilities handler
# ---------------------------------------------------------------------------


class TestCoreCapabilities:
    """core.capabilities returns the registry snapshot."""

    async def test_empty_initially(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        resp = await server.handle_command(_req("core.capabilities"), conn)
        assert resp.result == {}

    async def test_contains_registered_module(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        await _register(server, conn, name="vault")
        resp = await server.handle_command(_req("core.capabilities"), conn)
        assert "vault" in resp.result


# ---------------------------------------------------------------------------
# core.status handler — extended payload
# ---------------------------------------------------------------------------


class TestCoreStatus:
    """core.status returns the extended {core, modules} payload."""

    async def test_has_core_version(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        resp = await server.handle_command(_req("core.status"), conn)
        assert isinstance(resp.result["core"]["version"], str)

    async def test_uptime_is_nonnegative_float(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        resp = await server.handle_command(_req("core.status"), conn)
        uptime = resp.result["core"]["uptime_seconds"]
        assert isinstance(uptime, float) and uptime >= 0.0

    async def test_has_modules_section(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        resp = await server.handle_command(_req("core.status"), conn)
        assert resp.result["modules"] == {}

    async def test_module_status_reflects_state(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        await _register(server, conn, name="vault")
        resp = await server.handle_command(_req("core.status"), conn)
        assert resp.result["modules"]["vault"]["status"] == "registered"

    async def test_last_seen_none_before_heartbeat(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        await _register(server, conn, name="vault")
        resp = await server.handle_command(_req("core.status"), conn)
        assert resp.result["modules"]["vault"]["last_seen"] is None

    async def test_restart_count_present(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        await _register(server, conn, name="vault")
        resp = await server.handle_command(_req("core.status"), conn)
        assert resp.result["modules"]["vault"]["restart_count"] == 0


# ---------------------------------------------------------------------------
# core.subscribe handler — broker subscription
# ---------------------------------------------------------------------------


class TestCoreSubscribe:
    """core.subscribe creates a broker subscription and returns its id."""

    async def test_returns_subscription_id(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        resp = await server.handle_command(
            _req("core.subscribe", topics=["vault.*"]), conn
        )
        assert isinstance(resp.result["subscription_id"], int)

    async def test_distinct_ids_per_subscribe(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        first = await server.handle_command(
            _req("core.subscribe", req_id=1, topics=["vault.*"]), conn
        )
        second = await server.handle_command(
            _req("core.subscribe", req_id=2, topics=["oracle.*"]), conn
        )
        assert first.result["subscription_id"] != second.result["subscription_id"]

    async def test_empty_topics_is_invalid_params(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        resp = await server.handle_command(
            _req("core.subscribe", topics=[]), conn
        )
        assert resp.error is not None and resp.error["code"] == -32602


# ---------------------------------------------------------------------------
# Module-method dispatch — 4B: always -31000 (no routing)
# ---------------------------------------------------------------------------


class TestModuleMethodDispatch:
    """In v0.2.0 (4B) any module-namespaced method returns module offline."""

    async def test_module_method_is_offline(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        resp = await server.handle_command(_req("vault.unlock"), conn)
        assert resp.error is not None and resp.error["code"] == -31000

    async def test_module_method_offline_even_if_registered(
        self, tmp_path: Any
    ) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        await _register(server, conn, name="vault", methods=["vault.unlock"])
        resp = await server.handle_command(_req("vault.unlock"), conn)
        assert resp.error is not None and resp.error["code"] == -31000


# ---------------------------------------------------------------------------
# Error mapping — Python exceptions / bad input -> wire codes (§6.5)
# ---------------------------------------------------------------------------


class TestErrorMapping:
    """Centralized exception-to-wire-error mapping."""

    async def test_unknown_core_method_is_method_not_found(
        self, tmp_path: Any
    ) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        resp = await server.handle_command(_req("core.bogus"), conn)
        assert resp.error is not None and resp.error["code"] == -32601

    async def test_register_missing_param_is_invalid_params(
        self, tmp_path: Any
    ) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        resp = await server.handle_command(
            _req("core.register", version="1.0", methods=[], events=[]), conn
        )
        assert resp.error is not None and resp.error["code"] == -32602

    async def test_forged_token_is_not_authorized(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        conn.token = "forged.token"
        resp = await server.handle_command(_req("core.capabilities"), conn)
        assert resp.error is not None and resp.error["code"] == -31007

    async def test_error_response_echoes_request_id(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        resp = await server.handle_command(_req("core.bogus", req_id=99), conn)
        assert resp.id == 99


# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------


class TestGracefulShutdown:
    """stop() closes and unlinks both sockets and is idempotent."""

    async def test_sockets_unlinked_after_stop(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        await server.start()
        await server.stop()
        assert not (tmp_path / "core.sock").exists()
        assert not (tmp_path / "events.sock").exists()

    async def test_double_stop_is_safe(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        await server.start()
        await server.stop()
        await server.stop()  # no error

    async def test_stop_without_start_is_safe(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        await server.stop()  # no error


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    """async with Server(...) starts on enter, stops on exit."""

    async def test_sockets_exist_inside_context(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        async with server:
            assert (tmp_path / "core.sock").exists()

    async def test_sockets_gone_after_context(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        async with server:
            pass
        assert not (tmp_path / "core.sock").exists()


# ---------------------------------------------------------------------------
# Real-socket integration (E2E)
# ---------------------------------------------------------------------------


class TestRealSocketIntegration:
    """End-to-end over real UNIX sockets in tmp_path."""

    async def test_capabilities_over_socket(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        await server.start()
        try:
            line = '{"jsonrpc":"2.0","id":1,"method":"core.capabilities"}\n'
            resp = await _roundtrip(tmp_path / "core.sock", line)
            assert isinstance(resp, Response) and resp.result == {}
        finally:
            await server.stop()

    async def test_register_over_socket(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        await server.start()
        try:
            reg = (
                '{"jsonrpc":"2.0","id":1,"method":"core.register","params":'
                '{"module":"vault","version":"1.0","methods":["vault.unlock"],'
                '"events":[],"depends_on":[]}}\n'
            )
            resp = await _roundtrip(tmp_path / "core.sock", reg)
            assert resp.error is None
        finally:
            await server.stop()

    async def test_malformed_json_is_parse_error(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        await server.start()
        try:
            resp = await _roundtrip(tmp_path / "core.sock", "not json at all\n")
            assert resp.error is not None and resp.error["code"] == -32700
        finally:
            await server.stop()

    async def test_response_is_newline_terminated(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        await server.start()
        try:
            reader, writer = await asyncio.open_unix_connection(
                str(tmp_path / "core.sock")
            )
            try:
                writer.write(
                    b'{"jsonrpc":"2.0","id":1,"method":"core.capabilities"}\n'
                )
                await writer.drain()
                raw = await asyncio.wait_for(reader.readline(), timeout=2.0)
                assert raw.endswith(b"\n")
            finally:
                writer.close()
                await writer.wait_closed()
        finally:
            await server.stop()

    async def test_unknown_method_over_socket(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        await server.start()
        try:
            line = '{"jsonrpc":"2.0","id":7,"method":"core.bogus"}\n'
            resp = await _roundtrip(tmp_path / "core.sock", line)
            assert resp.error is not None and resp.error["code"] == -32601
        finally:
            await server.stop()

    async def test_event_pushed_to_subscriber(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        await server.start()
        try:
            # Subscribe on events.sock, then trigger module.registered via a
            # register on core.sock; the notification must be pushed.
            ev_reader, ev_writer = await asyncio.open_unix_connection(
                str(tmp_path / "events.sock")
            )
            try:
                # Subscribe to the exact topic — module.* would also match the
                # module.state_changed events that lifecycle emits during the
                # register orchestration, and would deliver one of those first.
                ev_writer.write(
                    b'{"jsonrpc":"2.0","id":1,"method":"core.subscribe",'
                    b'"params":{"topics":["module.registered"]}}\n'
                )
                await ev_writer.drain()
                await asyncio.wait_for(ev_reader.readline(), timeout=2.0)  # sub ack
                reg = (
                    '{"jsonrpc":"2.0","id":2,"method":"core.register","params":'
                    '{"module":"vault","version":"1.0","methods":[],'
                    '"events":[],"depends_on":[]}}\n'
                )
                await _roundtrip(tmp_path / "core.sock", reg)
                pushed = await asyncio.wait_for(ev_reader.readline(), timeout=2.0)
                note = parse(pushed.decode())
                assert note.method == "module.registered"
            finally:
                ev_writer.close()
                await ev_writer.wait_closed()
        finally:
            await server.stop()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Boundary conditions that often hide bugs."""

    async def test_unicode_module_name(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        await _register(server, conn, name="сховище")
        caps = await server.handle_command(_req("core.capabilities"), conn)
        assert "сховище" in caps.result

    async def test_register_empty_name_is_invalid_params(
        self, tmp_path: Any
    ) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        resp = await server.handle_command(
            _req("core.register", module="", version="1.0", methods=[], events=[]),
            conn,
        )
        assert resp.error is not None and resp.error["code"] == -32602

    async def test_status_before_any_register(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        resp = await server.handle_command(_req("core.status"), conn)
        assert resp.result["modules"] == {}

    async def test_success_response_echoes_request_id(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        resp = await server.handle_command(_req("core.capabilities", req_id=42), conn)
        assert resp.id == 42
