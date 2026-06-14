"""C2c: core.echo.shape / core.echo.unshape operator commands -> EchoShaperClient.

No-client case is a pure unit; forwarding uses an injected fake client OBJECT (no socket).
Mirrors test_core_lock.py. RED until the handlers land.
"""

from core.broker import EventBroker
from core.config import CoreConfig
from core.envelope import Request
from core.errors import JSONRPC_INVALID_PARAMS, ChimeraError
from core.lifecycle import Lifecycle
from core.registry import Registry
from core.server import Server
from core.tokens import TokenIssuer


class _FakeShaperClient:
    """Stand-in EchoShaperClient: records what core forwards, no socket."""

    def __init__(self):
        self.shaped = None
        self.unshaped = 0

    async def shape(self, rate_kbps):
        self.shaped = rate_kbps
        return {"ok": True, "rate_kbps": rate_kbps}

    async def unshape(self):
        self.unshaped += 1
        return {"ok": True}


def _server(tmp_path, echo_shaper_client=None):
    config = CoreConfig.model_validate({"socket_dir": str(tmp_path)})
    broker = EventBroker()
    lifecycle = Lifecycle(config, broker)
    registry = Registry(lifecycle, broker)
    return Server(
        config,
        registry,
        lifecycle,
        broker,
        TokenIssuer(),
        echo_shaper_client=echo_shaper_client,
    )


def _req(method, params=None):
    return Request(jsonrpc="2.0", id=1, method=method, params=params)


async def test_shape_without_client_precondition(tmp_path):
    server = _server(tmp_path, echo_shaper_client=None)
    conn = server.new_connection()
    resp = await server.handle_command(_req("core.echo.shape", {"rate_kbps": 256}), conn)
    assert resp.error is not None
    assert resp.error["code"] == ChimeraError.PRECONDITION_FAILED


async def test_shape_forwards_rate_to_client(tmp_path):
    fake = _FakeShaperClient()
    server = _server(tmp_path, echo_shaper_client=fake)
    conn = server.new_connection()
    resp = await server.handle_command(_req("core.echo.shape", {"rate_kbps": 256}), conn)
    assert resp.error is None
    assert resp.result == {"ok": True, "rate_kbps": 256}
    assert fake.shaped == 256


async def test_shape_rejects_bad_rate(tmp_path):
    fake = _FakeShaperClient()
    server = _server(tmp_path, echo_shaper_client=fake)
    conn = server.new_connection()
    resp = await server.handle_command(_req("core.echo.shape", {"rate_kbps": 0}), conn)
    assert resp.error is not None
    assert resp.error["code"] == JSONRPC_INVALID_PARAMS
    assert fake.shaped is None  # never forwarded on a bad rate


async def test_unshape_forwards_to_client(tmp_path):
    fake = _FakeShaperClient()
    server = _server(tmp_path, echo_shaper_client=fake)
    conn = server.new_connection()
    resp = await server.handle_command(_req("core.echo.unshape"), conn)
    assert resp.error is None
    assert resp.result == {"ok": True}
    assert fake.unshaped == 1
