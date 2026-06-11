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
import logging
import os
import stat
from typing import Any

from core.broker import Event, EventBroker
from core.config import CoreConfig
from core.envelope import Request, Response, parse, serialize_frame
from core.errors import ChimeraError
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


def _make_server(tmp_path: Any, request_timeout_s: float | None = None) -> Server:
    """Full DI wiring with sockets under tmp_path. TokenIssuer uses real time
    (TTL is 3600s; tests run in milliseconds). request_timeout_s overrides the
    routing deadline for fast timeout tests."""
    data: dict[str, Any] = {"socket_dir": str(tmp_path)}
    if request_timeout_s is not None:
        data["request_timeout_s"] = request_timeout_s
    config = CoreConfig.model_validate(data)
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


async def _roundtrip(sock_path: Any, line: str, timeout_s: float = 2.0) -> Response:
    """Open a UNIX connection, send one NDJSON frame, read one response frame."""
    reader, writer = await asyncio.open_unix_connection(str(sock_path))
    try:
        writer.write(line.encode())
        await writer.drain()
        raw = await asyncio.wait_for(reader.readline(), timeout=timeout_s)
        return parse(raw.decode())
    finally:
        writer.close()
        await writer.wait_closed()


def _mode(path: Any) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)


class FakeWriter:
    """A StreamWriter stand-in for unit-testing the router without a socket.

    Captures every frame the server forwards to a module's connection so a
    test can read the assigned internal id and simulate the module's reply.
    """

    def __init__(self) -> None:
        self._chunks: list[bytes] = []

    def write(self, data: bytes) -> None:
        self._chunks.append(data)

    async def drain(self) -> None:
        return None

    def frames(self) -> list[str]:
        return b"".join(self._chunks).decode().splitlines()

    def last_request(self) -> Request:
        msg = parse(self.frames()[-1])
        assert isinstance(msg, Request)
        return msg


async def _attach_registered_module(
    server: Server, name: str = "vault", methods: list[str] | None = None
) -> tuple[Connection, FakeWriter]:
    """Register a module and attach a FakeWriter as its live connection (seam-B)."""
    conn = server.new_connection()
    await server.handle_command(
        _req(
            "core.register",
            module=name,
            version="1.0",
            methods=methods if methods is not None else [f"{name}.do"],
            events=[],
        ),
        conn,
    )
    fake = FakeWriter()
    server._attach_module_writer(name, fake)
    return conn, fake


async def _module_caller(server: Server, name: str = "oracle") -> Connection:
    """A connection that has registered as a module (is_module=True)."""
    conn = server.new_connection()
    await server.handle_command(
        _req("core.register", module=name, version="1.0", methods=[], events=[]),
        conn,
    )
    return conn


async def _routed_call(
    server: Server,
    surface: Connection,
    module_conn: Connection,
    fake: FakeWriter,
    method: str,
    req_id: int = 1,
    params: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
    wait: float = 1.0,
) -> Response:
    """Drive a full route: surface request -> forwarded frame -> module reply."""
    task = asyncio.create_task(
        server.handle_command(_req(method, req_id, **(params or {})), surface)
    )
    await asyncio.sleep(0)  # let _route forward + register the pending future
    forwarded = fake.last_request()
    if error is not None:
        reply = Response(jsonrpc="2.0", id=forwarded.id, error=error)
    else:
        reply = Response(
            jsonrpc="2.0", id=forwarded.id, result=result if result is not None else {"ok": True}
        )
    await server._handle_line(serialize_frame(reply), module_conn)
    return await asyncio.wait_for(task, timeout=wait)


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

    async def test_reactive_section_pulse_mode_default(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        resp = await server.handle_command(_req("core.status"), conn)
        assert resp.result["reactive"]["pulse_mode"] == "normal"  # no PULSE event yet

    async def test_reactive_section_reflects_pulse_mode(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        server._pulse_mode = "tired"
        conn = server.new_connection()
        resp = await server.handle_command(_req("core.status"), conn)
        assert resp.result["reactive"]["pulse_mode"] == "tired"

    async def test_reactive_section_lists_armed_reflexes(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        resp = await server.handle_command(_req("core.status"), conn)
        reflexes = resp.result["reactive"]["reflexes"]
        assert any("tether.absent" in r for r in reflexes)
        assert any("exhausted" in r for r in reflexes)


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
    """A module method whose owner is unregistered returns module offline.

    (The former 4B test 'offline even if registered' was rewritten for the 4A
    router as TestRouteResolution.test_registered_connected_module_method_routes
    — under 4A a registered+connected module's method is routed, not -31000.)
    """

    async def test_module_method_is_offline(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
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


# ===========================================================================
# Router 4A — forward module.method to the owning module's connection
# ===========================================================================


class TestRouteAuthorization:
    """D7: module-method authz uses conn.is_module (tokens.py untouched)."""

    async def test_surface_caller_is_routed(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        surface = server.new_connection()
        modconn, fake = await _attach_registered_module(server, "vault", ["vault.do"])
        resp = await _routed_call(server, surface, modconn, fake, "vault.do", 1)
        assert resp.error is None  # surface is allowed to route

    async def test_module_caller_other_module_denied(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        caller = await _module_caller(server, "oracle")  # is_module = True
        resp = await server.handle_command(_req("vault.do"), caller)
        assert resp.error is not None and resp.error["code"] == -31007

    async def test_module_caller_own_namespace_denied(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        caller = await _module_caller(server, "vault")  # registered as vault
        resp = await server.handle_command(_req("vault.do"), caller)
        assert resp.error is not None and resp.error["code"] == -31007


class TestRouteResolution:
    """D8: granular resolution — offline / capability-missing / routes."""

    async def test_unregistered_module_offline(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        surface = server.new_connection()
        resp = await server.handle_command(_req("ghost.do"), surface)
        assert resp.error is not None and resp.error["code"] == -31000

    async def test_registered_method_not_advertised_capability_missing(
        self, tmp_path: Any
    ) -> None:
        server = _make_server(tmp_path)
        surface = server.new_connection()
        await _attach_registered_module(server, "vault", ["vault.unlock"])
        resp = await server.handle_command(_req("vault.lock"), surface)
        assert resp.error is not None and resp.error["code"] == -31002

    async def test_registered_without_connection_offline(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        modconn = server.new_connection()
        await server.handle_command(
            _req("core.register", module="vault", version="1.0", methods=["vault.do"], events=[]),
            modconn,
        )  # registered but NO _attach_module_writer — no live connection
        surface = server.new_connection()
        resp = await server.handle_command(_req("vault.do"), surface)
        assert resp.error is not None and resp.error["code"] == -31000

    async def test_registered_connected_module_method_routes(self, tmp_path: Any) -> None:
        # CONTRACT CHANGE: rewrites the former 4B test
        # 'test_module_method_offline_even_if_registered'. Under 4A a
        # registered + connected module's method is FORWARDED and its result
        # relayed — not short-circuited to -31000.
        server = _make_server(tmp_path)
        surface = server.new_connection()
        modconn, fake = await _attach_registered_module(server, "vault", ["vault.do"])
        resp = await _routed_call(
            server, surface, modconn, fake, "vault.do", 1, result={"unlocked": True}
        )
        assert resp.error is None
        assert resp.result == {"unlocked": True}


class TestRouteCorrelation:
    """D2: internal-id remap is collision-safe."""

    async def test_forwarded_request_uses_internal_id(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        surface = server.new_connection()
        modconn, fake = await _attach_registered_module(server, "vault", ["vault.do"])
        task = asyncio.create_task(server.handle_command(_req("vault.do", 5), surface))
        await asyncio.sleep(0)
        forwarded = fake.last_request()
        assert forwarded.id != 5  # core assigns a fresh internal id
        # resolve so the task completes cleanly
        await server._handle_line(
            serialize_frame(Response(jsonrpc="2.0", id=forwarded.id, result={"ok": True})),
            modconn,
        )
        await asyncio.wait_for(task, 1.0)

    async def test_response_id_rewritten_to_original(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        surface = server.new_connection()
        modconn, fake = await _attach_registered_module(server, "vault", ["vault.do"])
        resp = await _routed_call(server, surface, modconn, fake, "vault.do", 5)
        assert resp.id == 5

    async def test_same_original_id_no_collision(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        surface_a = server.new_connection()
        surface_b = server.new_connection()
        modconn, fake = await _attach_registered_module(server, "vault", ["vault.do"])
        task_a = asyncio.create_task(
            server.handle_command(_req("vault.do", 1, who="a"), surface_a)
        )
        task_b = asyncio.create_task(
            server.handle_command(_req("vault.do", 1, who="b"), surface_b)
        )
        await asyncio.sleep(0)
        reqs = [m for m in (parse(f) for f in fake.frames()) if isinstance(m, Request)]
        assert len(reqs) == 2
        assert reqs[0].id != reqs[1].id
        for r in reqs:
            assert isinstance(r.params, dict)
            await server._handle_line(
                serialize_frame(
                    Response(jsonrpc="2.0", id=r.id, result={"who": r.params["who"]})
                ),
                modconn,
            )
        resp_a = await asyncio.wait_for(task_a, 1.0)
        resp_b = await asyncio.wait_for(task_b, 1.0)
        assert resp_a.id == 1 and resp_b.id == 1
        assert resp_a.result == {"who": "a"}
        assert resp_b.result == {"who": "b"}


class TestRouteForwarding:
    """D6: the forwarded frame and the relayed response."""

    async def test_forwarded_method_and_params(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        surface = server.new_connection()
        modconn, fake = await _attach_registered_module(server, "vault", ["vault.do"])
        task = asyncio.create_task(
            server.handle_command(_req("vault.do", 1, x=7), surface)
        )
        await asyncio.sleep(0)
        forwarded = fake.last_request()
        assert forwarded.method == "vault.do"
        assert forwarded.params == {"x": 7}
        await server._handle_line(
            serialize_frame(Response(jsonrpc="2.0", id=forwarded.id, result={"ok": True})),
            modconn,
        )
        await asyncio.wait_for(task, 1.0)

    async def test_success_result_relayed(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        surface = server.new_connection()
        modconn, fake = await _attach_registered_module(server, "vault", ["vault.do"])
        resp = await _routed_call(
            server, surface, modconn, fake, "vault.do", 1, result={"value": 42}
        )
        assert resp.result == {"value": 42}

    async def test_error_relayed(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        surface = server.new_connection()
        modconn, fake = await _attach_registered_module(server, "vault", ["vault.do"])
        resp = await _routed_call(
            server, surface, modconn, fake, "vault.do", 1,
            error={"code": -31003, "message": "denied by policy"},
        )
        assert resp.error is not None and resp.error["code"] == -31003


class TestRouteTimeout:
    """D3: hybrid timeout — config default + per-method overrides (§6.8)."""

    async def test_known_method_timeout_overrides(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        assert server._timeout_for("vault.unlock") == 10.0
        assert server._timeout_for("oracle.classify") == 30.0
        assert server._timeout_for("oracle.ask") == 15.0  # NL-12a (cold LLM load)

    async def test_unknown_method_uses_config_default(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        assert server._timeout_for("foo.bar") == 5.0

    async def test_no_reply_times_out(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path, request_timeout_s=0.05)
        surface = server.new_connection()
        await _attach_registered_module(server, "vault", ["vault.do"])
        resp = await server.handle_command(_req("vault.do"), surface)  # no reply fed
        assert resp.error is not None and resp.error["code"] == -31001

    async def test_pending_cleared_after_timeout(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path, request_timeout_s=0.05)
        surface = server.new_connection()
        await _attach_registered_module(server, "vault", ["vault.do"])
        await server.handle_command(_req("vault.do"), surface)
        assert server._pending == {}


class TestRouteConcurrency:
    """D5: multiple in-flight requests to the same module."""

    async def test_two_inflight_resolved_independently(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        sa, sb = server.new_connection(), server.new_connection()
        modconn, fake = await _attach_registered_module(server, "vault", ["vault.do"])
        ta = asyncio.create_task(server.handle_command(_req("vault.do", 1, k="a"), sa))
        tb = asyncio.create_task(server.handle_command(_req("vault.do", 2, k="b"), sb))
        await asyncio.sleep(0)
        reqs = [m for m in (parse(f) for f in fake.frames()) if isinstance(m, Request)]
        for r in reqs:
            assert isinstance(r.params, dict)
            await server._handle_line(
                serialize_frame(Response(jsonrpc="2.0", id=r.id, result={"k": r.params["k"]})),
                modconn,
            )
        ra = await asyncio.wait_for(ta, 1.0)
        rb = await asyncio.wait_for(tb, 1.0)
        assert ra.result == {"k": "a"}
        assert rb.result == {"k": "b"}

    async def test_replies_out_of_order_matched(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        sa, sb = server.new_connection(), server.new_connection()
        modconn, fake = await _attach_registered_module(server, "vault", ["vault.do"])
        ta = asyncio.create_task(server.handle_command(_req("vault.do", 1, k="a"), sa))
        tb = asyncio.create_task(server.handle_command(_req("vault.do", 2, k="b"), sb))
        await asyncio.sleep(0)
        reqs = [m for m in (parse(f) for f in fake.frames()) if isinstance(m, Request)]
        for r in reversed(reqs):  # reply in reverse order
            assert isinstance(r.params, dict)
            await server._handle_line(
                serialize_frame(Response(jsonrpc="2.0", id=r.id, result={"k": r.params["k"]})),
                modconn,
            )
        ra = await asyncio.wait_for(ta, 1.0)
        rb = await asyncio.wait_for(tb, 1.0)
        assert ra.result == {"k": "a"}
        assert rb.result == {"k": "b"}


class TestRouteDisconnect:
    """D4: a module disconnect resolves its pending requests with -31000."""

    async def test_disconnect_resolves_pending_offline(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        surface = server.new_connection()
        await _attach_registered_module(server, "vault", ["vault.do"])
        task = asyncio.create_task(server.handle_command(_req("vault.do"), surface))
        await asyncio.sleep(0)  # request now pending
        server._detach_module_writer("vault")  # simulate disconnect
        resp = await asyncio.wait_for(task, 1.0)
        assert resp.error is not None and resp.error["code"] == -31000

    async def test_detach_removes_writer(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        surface = server.new_connection()
        await _attach_registered_module(server, "vault", ["vault.do"])
        server._detach_module_writer("vault")
        resp = await server.handle_command(_req("vault.do"), surface)
        assert resp.error is not None and resp.error["code"] == -31000

    async def test_detach_unknown_is_safe(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        server._detach_module_writer("ghost")  # no error


class TestRouteInboundResponse:
    """_handle_line routes an inbound Response to the pending future."""

    async def test_inbound_response_resolves_pending(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        surface = server.new_connection()
        modconn, fake = await _attach_registered_module(server, "vault", ["vault.do"])
        resp = await _routed_call(server, surface, modconn, fake, "vault.do", 3, result={"x": 1})
        assert resp.result == {"x": 1}

    async def test_unknown_response_id_ignored(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        conn = server.new_connection()
        out = await server._handle_line(
            serialize_frame(Response(jsonrpc="2.0", id=999999, result={"x": 1})), conn
        )
        assert out is None  # no pending with that id — ignored, no crash

    async def test_double_response_ignored(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        surface = server.new_connection()
        modconn, fake = await _attach_registered_module(server, "vault", ["vault.do"])
        resp = await _routed_call(server, surface, modconn, fake, "vault.do", 4, result={"x": 1})
        forwarded = fake.last_request()
        out = await server._handle_line(
            serialize_frame(Response(jsonrpc="2.0", id=forwarded.id, result={"x": 2})), modconn
        )
        assert out is None  # pending already resolved — second reply ignored
        assert resp.result == {"x": 1}  # original caller unaffected


# ---------------------------------------------------------------------------
# Router 4A — end-to-end over real sockets with a fake module client
# ---------------------------------------------------------------------------


async def _run_fake_module(
    sock_path: Any,
    name: str,
    methods: list[str],
    *,
    respond: bool = True,
    error: dict[str, Any] | None = None,
    disconnect_on_request: bool = False,
) -> None:
    """A minimal module client: registers, then answers forwarded requests."""
    reader, writer = await asyncio.open_unix_connection(str(sock_path))
    try:
        writer.write(
            serialize_frame(
                Request(
                    jsonrpc="2.0",
                    id=1,
                    method="core.register",
                    params={"module": name, "version": "1.0", "methods": methods, "events": []},
                )
            ).encode()
        )
        await writer.drain()
        await reader.readline()  # register ack
        while True:
            line = await reader.readline()
            if not line:
                break
            msg = parse(line.decode())
            if not isinstance(msg, Request):
                continue
            if disconnect_on_request:
                break
            if not respond:
                continue
            reply = (
                Response(jsonrpc="2.0", id=msg.id, error=error)
                if error is not None
                else Response(jsonrpc="2.0", id=msg.id, result={"ok": True})
            )
            writer.write(serialize_frame(reply).encode())
            await writer.drain()
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, BrokenPipeError):
            pass


async def _cancel(task: "asyncio.Task[None]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


class TestRealSocketRouting:
    """End-to-end routing over real UNIX sockets with a responding module."""

    async def test_e2e_round_trip(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        await server.start()
        mod = asyncio.create_task(
            _run_fake_module(tmp_path / "core.sock", "vault", ["vault.unlock"])
        )
        try:
            await asyncio.sleep(0.05)  # let the module register
            resp = await _roundtrip(
                tmp_path / "core.sock",
                '{"jsonrpc":"2.0","id":7,"method":"vault.unlock"}\n',
            )
            assert resp.error is None
            assert resp.result == {"ok": True}
            assert resp.id == 7
        finally:
            await _cancel(mod)
            await server.stop()

    async def test_e2e_timeout(self, tmp_path: Any) -> None:
        # Use a method WITHOUT a METHOD_TIMEOUTS override so the config default
        # (0.1s here) applies — 'vault.unlock' has a 10s override that would
        # outlast the client's read window.
        server = _make_server(tmp_path, request_timeout_s=0.1)
        await server.start()
        mod = asyncio.create_task(
            _run_fake_module(tmp_path / "core.sock", "vault", ["vault.do"], respond=False)
        )
        try:
            await asyncio.sleep(0.05)
            resp = await _roundtrip(
                tmp_path / "core.sock",
                '{"jsonrpc":"2.0","id":7,"method":"vault.do"}\n',
            )
            assert resp.error is not None and resp.error["code"] == -31001
        finally:
            await _cancel(mod)
            await server.stop()

    async def test_e2e_error_relayed(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        await server.start()
        mod = asyncio.create_task(
            _run_fake_module(
                tmp_path / "core.sock", "vault", ["vault.unlock"],
                error={"code": -31003, "message": "denied"},
            )
        )
        try:
            await asyncio.sleep(0.05)
            resp = await _roundtrip(
                tmp_path / "core.sock",
                '{"jsonrpc":"2.0","id":7,"method":"vault.unlock"}\n',
            )
            assert resp.error is not None and resp.error["code"] == -31003
        finally:
            await _cancel(mod)
            await server.stop()

    async def test_e2e_unregistered_offline(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        await server.start()
        try:
            resp = await _roundtrip(
                tmp_path / "core.sock",
                '{"jsonrpc":"2.0","id":7,"method":"vault.unlock"}\n',
            )
            assert resp.error is not None and resp.error["code"] == -31000
        finally:
            await server.stop()


class TestAnomalyRelay:
    """Idea #3 (path B): core relays a broker event to a module command.

    RED: Server._relay_handle is a no-op, so the dispatch tests (A/D) and the
    offline-log test (B) fail; the D7 wire-guard test (C) passes (proves the new
    capability does NOT open a wire hole — must stay green through GREEN); the
    unmapped-topic test (E) passes coincidentally (a no-op issues nothing) and
    gains real meaning in GREEN. _relay_handle is driven directly — hermetic, no
    sockets, no ORACLE (synthetic Event), so 3B lands before 3C.
    """

    _ANOMALY = "oracle.anomaly.detected"

    # A — happy path: a mapped event issues the target command and the relay
    # awaits the module's reply (core acts as authority, in-process).
    async def test_relay_issues_mapped_command(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        _modconn, fake = await _attach_registered_module(
            server, "tether", ["tether.heighten"]
        )
        task = asyncio.create_task(
            server._relay_handle(Event(topic=self._ANOMALY, payload={"score": 0.9}))
        )
        for _ in range(4):  # let the fan-out relay forward + register the pending future
            await asyncio.sleep(0)
        assert fake.frames(), "relay should have forwarded a command"
        forwarded = fake.last_request()
        assert forwarded.method == "tether.heighten"
        # Simulate tether's reply so the awaiting relay completes (no rewrite — the
        # relay has no external caller).
        server._resolve_pending(
            Response(jsonrpc="2.0", id=forwarded.id, result={"ok": True})
        )
        await task  # completes without raising

    # Fan-out: one event drives MULTIPLE module reflexes. A detected anomaly both
    # heightens TETHER's sensitivity AND locks the vault (defense in depth).
    async def test_anomaly_relays_to_both_tether_and_vault(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        _tc, tfake = await _attach_registered_module(
            server, "tether", ["tether.heighten"]
        )
        _vc, vfake = await _attach_registered_module(server, "vault", ["vault.lock"])
        task = asyncio.create_task(
            server._relay_handle(Event(topic=self._ANOMALY, payload={"score": 0.9}))
        )
        for _ in range(4):  # let both reflexes forward + register their pendings
            await asyncio.sleep(0)
        for fake in (tfake, vfake):
            if fake.frames():
                req = fake.last_request()
                server._resolve_pending(
                    Response(jsonrpc="2.0", id=req.id, result={"ok": True})
                )
        await task
        methods = set()
        if tfake.frames():
            methods.add(tfake.last_request().method)
        if vfake.frames():
            methods.add(vfake.last_request().method)
        assert methods == {"tether.heighten", "vault.lock"}

    # Active countermeasure: a detected anomaly also turns on CHAFF decoy traffic to
    # mask the operator's real activity (the organism obscures, not just locks).
    async def test_anomaly_starts_chaff_decoy_traffic(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        _cc, cfake = await _attach_registered_module(
            server, "chaff", ["chaff.generation.start"]
        )
        task = asyncio.create_task(
            server._relay_handle(Event(topic=self._ANOMALY, payload={"score": 0.9}))
        )
        for _ in range(4):
            await asyncio.sleep(0)
        assert cfake.frames(), "anomaly should start CHAFF decoy traffic"
        forwarded = cfake.last_request()
        assert forwarded.method == "chaff.generation.start"
        server._resolve_pending(
            Response(jsonrpc="2.0", id=forwarded.id, result={"ok": True})
        )
        await task

    # Active countermeasure (timing): a detected anomaly also starts ECHO traffic-timing
    # normalization — pairs with CHAFF (CHAFF hides volume, ECHO hides timing).
    async def test_anomaly_starts_echo_timing_normalization(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        _ec, efake = await _attach_registered_module(server, "echo", ["echo.start"])
        task = asyncio.create_task(
            server._relay_handle(Event(topic=self._ANOMALY, payload={"score": 0.9}))
        )
        for _ in range(4):
            await asyncio.sleep(0)
        assert efake.frames(), "anomaly should start ECHO timing normalization"
        forwarded = efake.last_request()
        assert forwarded.method == "echo.start"
        server._resolve_pending(
            Response(jsonrpc="2.0", id=forwarded.id, result={"ok": True})
        )
        await task

    # B — resilience: an offline target is logged, never raised; the relay returns.
    async def test_relay_offline_target_logged_not_raised(
        self, tmp_path: Any, caplog: Any
    ) -> None:
        server = _make_server(tmp_path)  # tether NOT registered/attached
        with caplog.at_level(logging.WARNING):
            await server._relay_handle(Event(topic=self._ANOMALY, payload={}))
        assert any(
            "tether" in r.getMessage().lower() or "offline" in r.getMessage().lower()
            for r in caplog.records
        ), "an offline relay target should be logged"

    # C — D7 invariant (regression-guard): a module may NOT invoke the relay target
    # over the wire. The new core authority path must not open a wire hole.
    async def test_d7_module_cannot_invoke_relay_target(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        await _attach_registered_module(server, "tether", ["tether.heighten"])
        module_conn = await _module_caller(server, "oracle")
        resp = await server.handle_command(_req("tether.heighten", 1), module_conn)
        assert resp.error is not None
        assert resp.error["code"] == ChimeraError.NOT_AUTHORIZED

    # D — timeout isolation: the target never replies; the relay forwards, times
    # out, logs, and does NOT raise (the consume loop must survive).
    async def test_relay_timeout_isolated(self, tmp_path: Any, caplog: Any) -> None:
        server = _make_server(tmp_path, request_timeout_s=0.05)
        _modconn, fake = await _attach_registered_module(
            server, "tether", ["tether.heighten"]
        )
        with caplog.at_level(logging.WARNING):
            await server._relay_handle(Event(topic=self._ANOMALY, payload={}))
        assert fake.frames(), "relay should forward before timing out"
        assert fake.last_request().method == "tether.heighten"

    # E — declarative: a topic with no RELAY_RULES entry issues nothing.
    async def test_relay_ignores_unmapped_topic(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        _modconn, fake = await _attach_registered_module(
            server, "tether", ["tether.heighten"]
        )
        await server._relay_handle(Event(topic="chaff.decoy.sent", payload={}))
        assert fake.frames() == []

    # tether.absent -> vault.lock: losing the paired phone auto-locks the open
    # vault (the "one mind" — VAULT reacting to TETHER, via core's authority).
    async def test_tether_absent_relays_vault_lock(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        _modconn, fake = await _attach_registered_module(
            server, "vault", ["vault.lock"]
        )
        task = asyncio.create_task(
            server._relay_handle(Event(topic="tether.absent", payload={}))
        )
        for _ in range(4):  # let the fan-out relay forward + register the pending future
            await asyncio.sleep(0)
        assert fake.frames(), "tether.absent should relay a command to VAULT"
        forwarded = fake.last_request()
        assert forwarded.method == "vault.lock"
        server._resolve_pending(
            Response(jsonrpc="2.0", id=forwarded.id, result={"ok": True})
        )
        await task  # completes without raising

    # De-escalation (the missing direction): when the threat passes — the paired phone
    # returns (tether.recovered) — the organism STANDS DOWN the obfuscation organs it
    # ramped up on threat. The reflex web can now go down, not only up.
    async def test_tether_recovered_stands_down_obfuscation(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        _cc, cfake = await _attach_registered_module(
            server, "chaff", ["chaff.generation.stop"]
        )
        _ec, efake = await _attach_registered_module(server, "echo", ["echo.stop"])
        task = asyncio.create_task(
            server._relay_handle(Event(topic="tether.recovered", payload={}))
        )
        for _ in range(4):
            await asyncio.sleep(0)
        assert cfake.frames(), "tether.recovered should stand down CHAFF"
        assert efake.frames(), "tether.recovered should stand down ECHO"
        cfwd, efwd = cfake.last_request(), efake.last_request()
        assert cfwd.method == "chaff.generation.stop"
        assert efwd.method == "echo.stop"
        server._resolve_pending(Response(jsonrpc="2.0", id=cfwd.id, result={"ok": True}))
        server._resolve_pending(Response(jsonrpc="2.0", id=efwd.id, result={"ok": True}))
        await task

    # Symmetric de-escalation on the MATCHING axis: the anomaly that ramped obfuscation
    # up clears (ORACLE's all-clear) -> stand the obfuscation organs down. Purer than the
    # tether.recovered proxy — same signal that raised them now lowers them.
    async def test_anomaly_cleared_stands_down_obfuscation(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        _cc, cfake = await _attach_registered_module(
            server, "chaff", ["chaff.generation.stop"]
        )
        _ec, efake = await _attach_registered_module(server, "echo", ["echo.stop"])
        task = asyncio.create_task(
            server._relay_handle(
                Event(topic="oracle.anomaly.cleared", payload={"score": 0.4})
            )
        )
        for _ in range(4):
            await asyncio.sleep(0)
        assert cfake.frames(), "anomaly cleared should stand down CHAFF"
        assert efake.frames(), "anomaly cleared should stand down ECHO"
        cfwd, efwd = cfake.last_request(), efake.last_request()
        assert cfwd.method == "chaff.generation.stop"
        assert efwd.method == "echo.stop"
        server._resolve_pending(Response(jsonrpc="2.0", id=cfwd.id, result={"ok": True}))
        server._resolve_pending(Response(jsonrpc="2.0", id=efwd.id, result={"ok": True}))
        await task


class TestPulseVaultReflex:
    """Cognitive reflex (the "one mind" reacting to the OPERATOR): entering PULSE's
    'exhausted' mode — the operator is critically fatigued — auto-locks the vault.
    Fired once on the transition INTO exhausted, on core's authority, errors isolated.
    """

    async def test_exhausted_locks_vault(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        _vc, vfake = await _attach_registered_module(server, "vault", ["vault.lock"])
        task = asyncio.create_task(server._apply_pulse_mode("exhausted"))
        for _ in range(4):  # let the reflex forward + register its pending future
            await asyncio.sleep(0)
        assert vfake.frames(), "entering exhausted should lock the vault"
        forwarded = vfake.last_request()
        assert forwarded.method == "vault.lock"
        server._resolve_pending(
            Response(jsonrpc="2.0", id=forwarded.id, result={"ok": True})
        )
        await task

    async def test_tired_does_not_lock(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        _vc, vfake = await _attach_registered_module(server, "vault", ["vault.lock"])
        await server._apply_pulse_mode("tired")  # friction mode, not a lock
        assert vfake.frames() == []
        assert server._pulse_mode == "tired"  # mode still tracked

    async def test_no_relock_when_already_exhausted(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        _vc, vfake = await _attach_registered_module(server, "vault", ["vault.lock"])
        server._pulse_mode = "exhausted"  # already there — no fresh transition
        await server._apply_pulse_mode("exhausted")
        assert vfake.frames() == []


class _FakeShim:
    """Minimal ShimClient stand-in capturing screen-lock requests."""

    def __init__(self) -> None:
        self.locked = 0

    async def lock(self) -> dict[str, Any]:
        self.locked += 1
        return {"ok": True}


class TestTetherEscalationReflex:
    """The dead-man's graduated teeth: core actuates TETHER's escalation requests
    (EMIT-ONLY in TETHER). L1 -> screen-lock (shim); L2 -> vault.lock; L3 (PURGE) is
    opt-in and NEVER auto-run.
    """

    def _esc(self, stage: str, action: str) -> Event:
        return Event(
            topic="tether.escalation",
            payload={"stage": stage, "action_requested": action, "grace_remaining": 0},
        )

    async def test_l1_locks_screen_via_shim(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        shim = _FakeShim()
        server._shim_client = shim  # type: ignore[assignment]
        await server._on_tether_escalation(self._esc("L1", "lock_screen"))
        assert shim.locked == 1

    async def test_l2_locks_vault(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        _vc, vfake = await _attach_registered_module(server, "vault", ["vault.lock"])
        task = asyncio.create_task(
            server._on_tether_escalation(self._esc("L2", "lock_vaults"))
        )
        for _ in range(4):
            await asyncio.sleep(0)
        assert vfake.frames(), "L2 should lock the vault"
        forwarded = vfake.last_request()
        assert forwarded.method == "vault.lock"
        server._resolve_pending(
            Response(jsonrpc="2.0", id=forwarded.id, result={"ok": True})
        )
        await task

    async def test_l3_never_auto_purges(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        shim = _FakeShim()
        server._shim_client = shim  # type: ignore[assignment]
        _vc, vfake = await _attach_registered_module(server, "vault", ["vault.lock"])
        await server._on_tether_escalation(self._esc("L3", "trigger_purge"))
        assert shim.locked == 0  # PURGE is opt-in — no screen lock, no vault lock, no wipe
        assert vfake.frames() == []
