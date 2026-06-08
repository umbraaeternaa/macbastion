"""core.override.set — operator sets the gate-override phrase (OS-1…OS-4).

Unit: drive handle_command on a bare Server (no sockets) with a surface / module
Connection. RED — _handle_override_set raises NotImplementedError until GREEN. Pins:
surface-only (a module connection -> -31007), needs an override_store (-31004), needs a
non-empty phrase (-32602), and a surface set makes the phrase verify.
"""

from core.broker import EventBroker
from core.config import CoreConfig
from core.envelope import Request
from core.errors import ChimeraError
from core.lifecycle import Lifecycle
from core.override import OverrideStore
from core.registry import Registry
from core.server import Server
from core.tokens import TokenIssuer


def _server(tmp_path, *, with_store=True):
    config = CoreConfig.model_validate({"socket_dir": str(tmp_path)})
    broker = EventBroker()
    lifecycle = Lifecycle(config, broker)
    registry = Registry(lifecycle, broker)
    store = OverrideStore(tmp_path / "override.json") if with_store else None
    return Server(config, registry, lifecycle, broker, TokenIssuer(), override_store=store)


def _req(phrase):
    params = {} if phrase is None else {"phrase": phrase}
    return Request(jsonrpc="2.0", id=1, method="core.override.set", params=params)


async def test_surface_sets_phrase(tmp_path):
    server = _server(tmp_path)
    conn = server.new_connection()  # surface-scoped
    resp = await server.handle_command(_req("let me in"), conn)
    assert resp.error is None
    assert resp.result["ok"] is True
    assert server._override_store.verify("let me in") is True


async def test_module_rejected(tmp_path):
    server = _server(tmp_path)
    conn = server.new_connection()
    conn.is_module = True  # a module must not set the operator's phrase
    resp = await server.handle_command(_req("x"), conn)
    assert resp.error["code"] == ChimeraError.NOT_AUTHORIZED


async def test_no_store_precondition(tmp_path):
    server = _server(tmp_path, with_store=False)
    conn = server.new_connection()
    resp = await server.handle_command(_req("x"), conn)
    assert resp.error["code"] == ChimeraError.PRECONDITION_FAILED


async def test_empty_phrase_invalid(tmp_path):
    server = _server(tmp_path)
    conn = server.new_connection()
    resp = await server.handle_command(_req(""), conn)
    assert resp.error["code"] == -32602  # JSONRPC_INVALID_PARAMS


async def test_missing_phrase_invalid(tmp_path):
    server = _server(tmp_path)
    conn = server.new_connection()
    resp = await server.handle_command(_req(None), conn)
    assert resp.error["code"] == -32602
