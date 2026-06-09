"""RED contract for the core entry point (SV-1). Fails while core/__main__.py is the
NotImplementedError stub; green once build_core / _config_from_env / serve_forever land.

Imports of core.__main__ are deferred into each test so the stub's module-level raise
fails the test (cleanly) instead of aborting collection of the whole suite.

Unit-level (no sockets): build_core just constructs a wired Server; _config_from_env
reads CHIMERA_SOCKET_DIR. Serving / signal behaviour is covered by the integration test.
"""

from core.config import CoreConfig
from core.server import Server


def test_build_core_returns_server(tmp_path):
    from core.__main__ import build_core

    cfg = CoreConfig.model_validate({"socket_dir": str(tmp_path)})
    assert isinstance(build_core(cfg), Server)


def test_build_core_instances_independent(tmp_path):
    from core.__main__ import build_core

    cfg = CoreConfig.model_validate({"socket_dir": str(tmp_path)})
    assert build_core(cfg) is not build_core(cfg)


def test_config_from_env_uses_socket_dir(monkeypatch, tmp_path):
    from core.__main__ import _config_from_env

    monkeypatch.setenv("CHIMERA_SOCKET_DIR", str(tmp_path))
    assert _config_from_env().socket_dir == tmp_path
