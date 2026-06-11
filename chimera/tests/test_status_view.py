"""render_status — the operator status surface (UX.md CLI). Pure render of the
core.status payload; RED until core/status_view.py renders it."""

from typing import Any

from core.status_view import render_status

SAMPLE: dict[str, Any] = {
    "core": {"version": "0.2.0", "uptime_seconds": 12.7},
    "modules": {
        "vault": {"version": "1.0", "status": "online", "methods": ["a", "b"], "events": []},
        "tether": {"version": "1.0", "status": "offline", "methods": ["x"], "events": []},
    },
}


def test_render_includes_core_header() -> None:
    out = render_status(SAMPLE)
    assert "CHIMERA" in out
    assert "0.2.0" in out  # core version


def test_render_lists_each_module_with_status() -> None:
    out = render_status(SAMPLE)
    assert "vault" in out and "online" in out
    assert "tether" in out and "offline" in out


def test_render_shows_module_count() -> None:
    out = render_status(SAMPLE)
    assert "2" in out  # two modules registered


def test_render_is_deterministic_module_order() -> None:
    # sorted by name -> tether before vault, stable across calls
    out = render_status(SAMPLE)
    assert out.index("tether") < out.index("vault")


def test_render_empty_modules_does_not_crash() -> None:
    out = render_status({"core": {"version": "0.2.0", "uptime_seconds": 0.0}, "modules": {}})
    assert "CHIMERA" in out  # header still rendered, no module rows


# --- integration: the `chimera status` subcommand over a real core socket ---
import pytest  # noqa: E402


@pytest.mark.integration
async def test_status_subcommand_renders_live_core(tmp_path: Any, capsys: Any) -> None:
    from core.__main__ import _status
    from core.broker import EventBroker
    from core.config import CoreConfig
    from core.lifecycle import Lifecycle
    from core.registry import Registry
    from core.server import Server
    from core.tokens import TokenIssuer

    config = CoreConfig.model_validate({"socket_dir": str(tmp_path)})
    broker = EventBroker()
    lifecycle = Lifecycle(config, broker)
    registry = Registry(lifecycle, broker)
    server = Server(config, registry, lifecycle, broker, TokenIssuer())
    await server.start()
    try:
        conn = server.new_connection()
        from core.envelope import Request

        await server.handle_command(
            Request(
                jsonrpc="2.0",
                id=1,
                method="core.register",
                params={
                    "module": "vault",
                    "version": "1.0",
                    "methods": ["vault.lock"],
                    "events": [],
                },
            ),
            conn,
        )
        rc = await _status(config)
        out = capsys.readouterr().out
        assert rc == 0
        assert "CHIMERA" in out
        assert "vault" in out
    finally:
        await server.stop()


async def test_status_subcommand_core_down_is_graceful(tmp_path: Any, capsys: Any) -> None:
    from core.__main__ import _status
    from core.config import CoreConfig

    config = CoreConfig.model_validate({"socket_dir": str(tmp_path)})  # no core running
    rc = await _status(config)
    out = capsys.readouterr().out
    assert rc == 1
    assert "not reachable" in out
