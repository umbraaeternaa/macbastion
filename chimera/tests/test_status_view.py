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


def test_render_shows_reactive_state() -> None:
    payload = {
        **SAMPLE,
        "reactive": {
            "pulse_mode": "tired",
            "reflexes": ["tether.absent -> vault.lock", "pulse:exhausted -> vault.lock"],
        },
    }
    out = render_status(payload)
    assert "tired" in out  # the live PULSE cognitive mode
    assert "tether.absent -> vault.lock" in out  # an armed reflex is listed
    assert "pulse:exhausted -> vault.lock" in out


def test_render_without_reactive_does_not_crash() -> None:
    out = render_status(SAMPLE)  # no "reactive" key -> still renders core + modules
    assert "CHIMERA" in out


def test_render_vault_open() -> None:
    vault = {"available": True, "open": True, "open_vault_id": "abcd"}
    out = render_status({**SAMPLE, "vault": vault})
    assert "VAULT: open" in out
    assert "abcd" in out  # which vault is open


def test_render_vault_locked() -> None:
    out = render_status({**SAMPLE, "vault": {"available": True, "open": False}})
    assert "VAULT: locked" in out


def test_render_vault_offline() -> None:
    out = render_status({**SAMPLE, "vault": {"available": False}})
    assert "VAULT: offline" in out


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
        assert "VAULT:" in out  # live vault-state line (offline here — no daemon attached)
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


# --- render_event: one pushed event -> a concise operator line (chimera watch) ---
from core.status_view import render_event  # noqa: E402


def test_render_event_tether_absent() -> None:
    out = render_event("tether.absent", {"how": "grace"})
    assert "TETHER" in out and "absent" in out.lower()


def test_render_event_escalation_shows_stage_and_action() -> None:
    out = render_event(
        "tether.escalation", {"stage": "L1", "action_requested": "lock_screen"}
    )
    assert "L1" in out and "lock_screen" in out


def test_render_event_pulse_mode_shows_mode() -> None:
    out = render_event("pulse.mode.changed", {"new_mode": "exhausted"})
    assert "PULSE" in out and "exhausted" in out


def test_render_event_purge_imminent() -> None:
    out = render_event("purge.imminent", {})
    assert "PURGE" in out


def test_render_event_generic_unknown_topic() -> None:
    out = render_event("chaff.decoy.sent", {"bytes": 512})
    assert "chaff.decoy.sent" in out  # falls back to topic (+ payload)


# --- render_audit: the reflex audit trail -> readable operator lines (chimera audit) ---
from core.status_view import render_audit  # noqa: E402

_AUDIT = [
    {"ts": 1_700_000_000.0, "topic": "tether.absent", "commands": ["vault.lock"], "outcome": "ok"},
    {
        "ts": 1_700_000_050.0,
        "topic": "oracle.anomaly.detected",
        "commands": ["chaff.generation.start"],
        "outcome": "error: module offline",
    },
]


def test_render_audit_shows_topic_command_and_outcome() -> None:
    out = render_audit(_AUDIT)
    assert "tether.absent" in out
    assert "vault.lock" in out
    assert "ok" in out
    assert "oracle.anomaly.detected" in out
    assert "module offline" in out  # the failure outcome is visible


def test_render_audit_formats_timestamp() -> None:
    out = render_audit(_AUDIT)
    assert "2023" in out  # ts 1_700_000_000 -> a 2023 wall-clock date, not a raw float


def test_render_audit_one_line_per_entry() -> None:
    out = render_audit(_AUDIT)
    body = [ln for ln in out.splitlines() if "->" in ln]
    assert len(body) == 2  # one rendered line per actuation


def test_render_audit_empty_does_not_crash() -> None:
    out = render_audit([])
    assert isinstance(out, str)
    assert "audit" in out.lower()  # a friendly header/empty notice, never a traceback


def test_audit_subcommand_prints_trail(tmp_path: Any, capsys: Any) -> None:
    # The `chimera audit` surface reads audit.jsonl off disk (no core socket needed —
    # works even when core is down) and prints the rendered trail.
    from core.__main__ import _audit
    from core.audit import AuditLog
    from core.config import CoreConfig

    AuditLog(tmp_path / "audit.jsonl").record(
        topic="tether.absent", commands=["vault.lock"], outcome="ok"
    )
    config = CoreConfig.model_validate({"socket_dir": str(tmp_path)})
    rc = _audit(config, 50)
    out = capsys.readouterr().out
    assert rc == 0
    assert "tether.absent" in out
    assert "vault.lock" in out


def test_audit_subcommand_empty_when_no_trail(tmp_path: Any, capsys: Any) -> None:
    from core.__main__ import _audit
    from core.config import CoreConfig

    config = CoreConfig.model_validate({"socket_dir": str(tmp_path)})  # no audit.jsonl
    rc = _audit(config, 50)
    out = capsys.readouterr().out
    assert rc == 0
    assert "no reflexes" in out.lower()  # friendly empty notice, exit 0


@pytest.mark.integration
async def test_watch_subcommand_streams_events(tmp_path: Any, capsys: Any) -> None:
    import asyncio
    import contextlib

    from core.__main__ import _watch
    from core.broker import Event, EventBroker
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
    task = asyncio.create_task(_watch(config))
    try:
        await asyncio.sleep(0.2)  # let watch connect + subscribe
        broker.publish(Event(topic="tether.absent", payload={"how": "grace"}))
        await asyncio.sleep(0.2)  # let the push reach watch + print
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        await server.stop()
    out = capsys.readouterr().out
    assert "watching" in out  # the subscribe banner
    assert "TETHER" in out  # the streamed event was rendered
