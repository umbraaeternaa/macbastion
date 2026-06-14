"""S: opt-in startup-injection of the EchoShaperClient into the core (EP-4, off by default).

build_core wires a real client into the Server only when the operator turns it on via the
CoreConfig flag; otherwise core.echo.shape stays a precondition failure (the shaper is opt-in).
"""

from core.__main__ import build_core
from core.config import CoreConfig
from core.echo_shaper_client import EchoShaperClient


def _config(tmp_path, **extra):
    return CoreConfig.model_validate({"socket_dir": str(tmp_path), **extra})


def test_echo_shaper_off_by_default(tmp_path):
    server = build_core(_config(tmp_path))
    assert server._echo_shaper_client is None  # opt-in (EP-4) — no client unless enabled


def test_echo_shaper_enabled_wires_client(tmp_path):
    server = build_core(_config(tmp_path, echo_shaper_enabled=True))
    assert isinstance(server._echo_shaper_client, EchoShaperClient)
