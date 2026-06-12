"""CHIMERA core entry point — run via `python -m core` (SV-1).

Wires and runs the unprivileged core: socket server, router, broker, registry, token
issuer, and the override store. In production launchd (a LaunchAgent) is the real
supervisor that launches and watches this process (§7.10); module daemons are brought
up separately (the SV-2 supervisor). This module is just "what launchd runs".
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import signal
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from core.audit import AuditLog
from core.broker import EventBroker
from core.config import CoreConfig
from core.lifecycle import Lifecycle
from core.override import OverrideStore
from core.registry import Registry
from core.server import Server
from core.shim_client import ShimClient, ShimError
from core.status_view import render_audit, render_event, render_status
from core.supervisor import CHIMERA_MODULES, ModuleSpec, Supervisor
from core.tokens import TokenIssuer


def build_core(config: CoreConfig) -> Server:
    """Construct a fully-wired (but not yet started) core Server from config."""
    broker = EventBroker()
    lifecycle = Lifecycle(config, broker)
    registry = Registry(lifecycle, broker)
    override = OverrideStore(config.socket_dir / "override.json")
    return Server(
        config, registry, lifecycle, broker, TokenIssuer(),
        override_store=override, shim_client=ShimClient(),
    )


def _config_from_env() -> CoreConfig:
    """Resolve config from the environment (CHIMERA_SOCKET_DIR, default ~/.config/chimera/run)."""
    socket_dir = os.environ.get("CHIMERA_SOCKET_DIR") or str(Path.home() / ".config/chimera/run")
    return CoreConfig.model_validate({"socket_dir": socket_dir})


async def serve_forever(server: Server) -> None:
    """Start the core, then serve until SIGTERM/SIGINT, then stop gracefully."""
    await server.start()
    loop = asyncio.get_running_loop()
    stop = loop.create_future()

    def _request_stop() -> None:
        if not stop.done():
            stop.set_result(None)

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _request_stop)
    try:
        await stop
    finally:
        await server.stop()


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse the chimera CLI: no subcommand = bare core; `up` = whole organism; `plist`."""
    parser = argparse.ArgumentParser(prog="chimera", description="CHIMERA core / organism control")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("up", help="start core and bring all modules up (the whole organism)")
    sub.add_parser("plist", help="print the LaunchAgent plist for `python -m core up`")
    sub.add_parser(
        "install", help="install the LaunchAgent so the organism runs at login (one command)"
    )
    sub.add_parser("uninstall", help="unload the LaunchAgent and remove its plist")
    sub.add_parser(
        "shim-check", help="diagnostic: ping the shim and attempt the per-boot-secret handshake"
    )
    sub.add_parser("status", help="print a live view of the organism (core + modules)")
    sub.add_parser("watch", help="stream the organism's critical events live (Ctrl-C to stop)")
    audit_p = sub.add_parser(
        "audit", help="print the reflex audit trail (what the organism actuated, and why)"
    )
    audit_p.add_argument(
        "-n", type=int, default=50, help="how many recent actuations to show (default 50)"
    )
    audit_p.add_argument(
        "--failures",
        action="store_true",
        help="show only actuations that did NOT succeed (did any reflex fail?)",
    )
    return parser.parse_args(argv)


def _chimera_root() -> Path:
    """The chimera project dir (holds modules/ and .venv). Unfrozen: this file's parent.parent.
    Frozen (the signed PyInstaller onedir at <root>/dist/chimera/chimera): derive from the
    executable location, or a CHIMERA_ROOT override. This lets the signed frozen core — the
    one the shim attests — still find the native module binaries and the interpreter that runs
    the Python modules."""
    env = os.environ.get("CHIMERA_ROOT")
    if env:
        return Path(env)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parents[2]  # dist/chimera/chimera -> chimera/
    return Path(__file__).resolve().parent.parent


def _module_python() -> str:
    """The interpreter that runs the Python modules (oracle/pulse). Unfrozen: sys.executable
    is already the venv python. Frozen: sys.executable is the frozen core itself, which can't
    run `-m oracle`, so use the project venv python (CHIMERA_PYTHON overrides)."""
    env = os.environ.get("CHIMERA_PYTHON")
    if env:
        return env
    if getattr(sys, "frozen", False):
        venv = _chimera_root() / ".venv/bin/python"
        return str(venv) if venv.exists() else "python3"
    return sys.executable


def module_binary(name: str) -> Path:
    """Resolve a module's daemon binary: modules/<name>/<name>."""
    return _chimera_root() / "modules" / name / name


def _spawn_argv(
    spec: ModuleSpec, socket_dir: Path
) -> tuple[list[str], dict[str, str], str]:
    """The (argv, env, cwd) to launch one module pointed at socket_dir. A native module is
    its own binary (modules/NAME/NAME); a Python module runs as `python -m NAME` with its
    package dir on PYTHONPATH. cwd is the module's own directory so it finds files it reads
    relative to the working dir (e.g. CHAFF's data/endpoints.json). Pure + unit-testable."""
    module_dir = module_binary(spec.name).parent
    env = {
        "CHIMERA_SOCKET_DIR": str(socket_dir),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }
    if spec.python:
        env["PYTHONPATH"] = str(module_dir)
        return [_module_python(), "-m", spec.name], env, str(module_dir)
    return [str(module_binary(spec.name))], env, str(module_dir)


def _default_spawn(socket_dir: Path) -> Callable[[ModuleSpec], subprocess.Popen[bytes]]:
    """Build a spawn() that launches each module (native binary or `python -m`) at socket_dir."""

    def spawn(spec: ModuleSpec) -> subprocess.Popen[bytes]:
        argv, env, cwd = _spawn_argv(spec, socket_dir)
        return subprocess.Popen(  # noqa: S603 (trusted: our own modules)
            argv, env=env, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    return spawn


async def run_up(config: CoreConfig) -> None:
    """`chimera up`: start core, bring modules up in waves, auto-restart on FAILED, serve
    until a signal, then tear down."""
    config.socket_dir.mkdir(parents=True, exist_ok=True)
    server = build_core(config)
    await server.start()
    sup = Supervisor(
        CHIMERA_MODULES,
        spawn=_default_spawn(config.socket_dir),
        is_registered=server._registry.is_registered,  # noqa: SLF001 (internal wiring)
    )
    sub = server._broker.subscribe(  # noqa: SLF001
        [Lifecycle.STATE_CHANGED_TOPIC, "purge.imminent"]
    )
    loop = asyncio.get_running_loop()
    stop = loop.create_future()

    def _request_stop() -> None:
        if not stop.done():
            stop.set_result(None)

    async def _monitor() -> None:
        # Autonomy link: core's sweep marks a hung module FAILED -> we re-spawn it.
        # Emergency choreography: core.purge publishes purge.imminent -> SIGKILL the modules.
        while True:
            event = await sub.get()
            if event.topic == "purge.imminent":
                await sup.purge_kill()
            else:
                sup.on_state_changed(event.payload, server._lifecycle)  # noqa: SLF001

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _request_stop)
    monitor = asyncio.create_task(_monitor())
    try:
        await sup.up()
        await stop
    finally:
        monitor.cancel()
        server._broker.unsubscribe(sub)  # noqa: SLF001
        await sup.down()
        await server.stop()


def launch_agent_plist(socket_dir: Path) -> str:
    """The LaunchAgent plist XML that runs core `up` (§7.10).

    A signed frozen binary (PyInstaller, deploy/build-core.sh) IS the entry point, so it
    takes `up` directly; the dev interpreter needs `-m core up`.
    """
    program = (
        [sys.executable, "up"]
        if getattr(sys, "frozen", False)
        else [sys.executable, "-m", "core", "up"]
    )
    args_xml = "".join(f"        <string>{a}</string>\n" for a in program)
    chimera_dir = _chimera_root()  # cwd for the agent; frozen-aware (finds modules/ + .venv)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n'
        "<dict>\n"
        "    <key>Label</key>\n"
        "    <string>com.umbra.chimera</string>\n"
        "    <key>ProgramArguments</key>\n"
        f"    <array>\n{args_xml}    </array>\n"
        "    <key>EnvironmentVariables</key>\n"
        "    <dict>\n"
        "        <key>CHIMERA_SOCKET_DIR</key>\n"
        f"        <string>{socket_dir}</string>\n"
        "    </dict>\n"
        "    <key>WorkingDirectory</key>\n"
        f"    <string>{chimera_dir}</string>\n"
        "    <key>RunAtLoad</key>\n    <true/>\n"
        "    <key>KeepAlive</key>\n    <true/>\n"
        "</dict>\n</plist>\n"
    )


def _launch_agent_path() -> Path:
    """Where CHIMERA's persistence agent lives: the per-user LaunchAgents dir."""
    return Path.home() / "Library/LaunchAgents/com.umbra.chimera.plist"


def _bootstrap_argv(plist: Path) -> list[str]:
    """`launchctl bootstrap gui/<uid> <plist>` — load the agent into the user GUI domain."""
    return ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist)]


def _bootout_argv(plist: Path) -> list[str]:
    """`launchctl bootout gui/<uid> <plist>` — unload the agent from the user GUI domain."""
    return ["launchctl", "bootout", f"gui/{os.getuid()}", str(plist)]


def _install(config: CoreConfig) -> int:
    """`chimera install`: write the LaunchAgent plist and (re)load it, so the organism
    starts at login and restarts if it crashes (§7.10). Idempotent — any prior instance is
    booted out first, so re-running updates the plist instead of failing on 'already
    bootstrapped'. Returns a process exit code (the launchctl side effects are manual-tier;
    the plist content + argv are unit-tested)."""
    plist = _launch_agent_path()
    plist.parent.mkdir(parents=True, exist_ok=True)
    plist.write_text(launch_agent_plist(config.socket_dir))
    # Unload any prior instance first (ignore failure — it may simply not be loaded yet).
    subprocess.run(_bootout_argv(plist), capture_output=True, check=False)  # noqa: S603
    done = subprocess.run(  # noqa: S603
        _bootstrap_argv(plist), capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        print(f"wrote plist at {plist}, but `launchctl bootstrap` failed:")
        print(f"  {done.stderr.strip()}")
        return 1
    print(f"CHIMERA installed — runs at login, restarts on crash.\n  plist: {plist}")
    print("  remove any time with:  python -m core uninstall")
    return 0


def _uninstall() -> int:
    """`chimera uninstall`: unload the LaunchAgent and remove its plist. Idempotent — a
    missing or already-unloaded agent is a friendly no-op, not an error. Returns 0."""
    plist = _launch_agent_path()
    subprocess.run(_bootout_argv(plist), capture_output=True, check=False)  # noqa: S603
    existed = plist.exists()
    plist.unlink(missing_ok=True)
    if existed:
        print(f"CHIMERA uninstalled — agent unloaded, plist removed ({plist}).")
    else:
        print("CHIMERA not installed — nothing to remove.")
    return 0


async def _shim_check() -> int:
    """Diagnostic: ping the shim, then attempt the per-boot-secret handshake. Prints the
    outcome (never the secret itself) and returns a process exit code. The handshake succeeds
    only when the shim attests this process as the signed core (Slice 2b)."""
    sock = os.environ.get("CHIMERA_SHIM_SOCKET")
    client = ShimClient(sock) if sock else ShimClient()
    try:
        await client.ping()
        print("ping: pong")
    except ShimError as exc:
        print(f"ping: FAILED — {exc}")
        return 1
    try:
        secret = await client.handshake()
        print(f"handshake: ok — secret obtained ({len(secret)} hex chars)")
        return 0
    except ShimError as exc:
        print(f"handshake: DENIED — {exc}")
        return 1


async def _fetch(sock: Path, method: str) -> dict[str, Any] | None:
    """Send one JSON-RPC request over core.sock and return the parsed reply, or None if
    core is unreachable. The reply carries either a 'result' or an 'error'."""
    try:
        reader, writer = await asyncio.open_unix_connection(str(sock))
    except (FileNotFoundError, ConnectionRefusedError, OSError):
        return None
    try:
        req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method})
        writer.write((req + "\n").encode())
        await writer.drain()
        raw = await asyncio.wait_for(reader.readline(), timeout=5.0)
    finally:
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()
    parsed: dict[str, Any] = json.loads(raw.decode())
    return parsed


async def _status(config: CoreConfig) -> int:
    """`chimera status`: print the live organism view (core + modules + reactive state +
    VAULT open/locked). A core that isn't running -> a friendly message + exit 1."""
    sock = config.socket_dir / "core.sock"
    core_msg = await _fetch(sock, "core.status")
    if core_msg is None:
        print(f"core not reachable at {sock} — is `chimera up` running?")
        return 1
    result = core_msg.get("result")
    if result is None:
        print(f"core.status error: {core_msg.get('error')}")
        return 1
    # Live VAULT state (routed to the daemon; an offline/erroring module shows as offline).
    vault_msg = await _fetch(sock, "vault.status")
    vres = vault_msg.get("result") if vault_msg else None
    if vres is not None:
        result["vault"] = {
            "available": True,
            "open": bool(vres.get("vault_open")),
            "open_vault_id": vres.get("open_vault_id", ""),
        }
    else:
        result["vault"] = {"available": False}
    print(render_status(result))
    return 0


WATCH_TOPICS = [
    "tether.absent",
    "tether.escalation",
    "tether.recovered",
    "pulse.mode.changed",
    "oracle.anomaly.detected",
    "purge.imminent",
    "vault.locked",
    "vault.unlocked",
    "vault.relocked",
]


async def _watch(config: CoreConfig) -> int:
    """`chimera watch`: subscribe to the organism's critical events on events.sock and
    print each as it fires (Ctrl-C to stop). A core that isn't running -> exit 1."""
    sock = config.socket_dir / "events.sock"
    try:
        reader, writer = await asyncio.open_unix_connection(str(sock))
    except (FileNotFoundError, ConnectionRefusedError, OSError):
        print(f"core not reachable at {sock} — is `chimera up` running?")
        return 1
    try:
        req = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "core.subscribe",
                "params": {"topics": WATCH_TOPICS},
            }
        )
        writer.write((req + "\n").encode())
        await writer.drain()
        await reader.readline()  # subscribe ack
        print(f"watching {len(WATCH_TOPICS)} topics — Ctrl-C to stop")
        while True:
            raw = await reader.readline()
            if not raw:
                break
            msg = json.loads(raw.decode())
            method = msg.get("method")
            if method:  # a pushed Notification (events have a method, no id)
                print(render_event(method, msg.get("params") or {}))
    finally:
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()
    return 0


def _audit(config: CoreConfig, n: int, failures_only: bool = False) -> int:
    """`chimera audit`: print the reflex audit trail. Reads audit.jsonl straight off
    disk — no core socket needed, so it works even when core is down. With
    failures_only, show only actuations that did NOT succeed. Always exit 0
    (an empty/absent trail is a friendly notice, not an error)."""
    log = AuditLog(config.socket_dir / "audit.jsonl")
    print(render_audit(log.recent(n, failures_only=failures_only)))
    return 0


def main(argv: list[str] | None = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.command == "shim-check":  # standalone diagnostic — needs no core config
        raise SystemExit(asyncio.run(_shim_check()))
    config = _config_from_env()
    if args.command == "status":
        raise SystemExit(asyncio.run(_status(config)))
    if args.command == "watch":
        raise SystemExit(asyncio.run(_watch(config)))
    if args.command == "audit":
        raise SystemExit(_audit(config, args.n, args.failures))
    if args.command == "plist":
        print(launch_agent_plist(config.socket_dir))
        return
    if args.command == "install":
        raise SystemExit(_install(config))
    if args.command == "uninstall":
        raise SystemExit(_uninstall())
    if args.command == "up":
        asyncio.run(run_up(config))
        return
    config.socket_dir.mkdir(parents=True, exist_ok=True)
    asyncio.run(serve_forever(build_core(config)))


if __name__ == "__main__":
    main()
