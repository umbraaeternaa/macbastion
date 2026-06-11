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

from core.broker import EventBroker
from core.config import CoreConfig
from core.lifecycle import Lifecycle
from core.override import OverrideStore
from core.registry import Registry
from core.server import Server
from core.shim_client import ShimClient, ShimError
from core.status_view import render_status
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
        "shim-check", help="diagnostic: ping the shim and attempt the per-boot-secret handshake"
    )
    sub.add_parser("status", help="print a live view of the organism (core + modules)")
    return parser.parse_args(argv)


def module_binary(name: str) -> Path:
    """Resolve a module's daemon binary: modules/<name>/<name>."""
    return Path(__file__).resolve().parent.parent / "modules" / name / name


def _default_spawn(socket_dir: Path) -> Callable[[ModuleSpec], subprocess.Popen[bytes]]:
    """Build a spawn() that launches module binaries pointed at this socket_dir."""

    def spawn(spec: ModuleSpec) -> subprocess.Popen[bytes]:
        return subprocess.Popen(  # noqa: S603 (trusted: our own built module binary)
            [str(module_binary(spec.name))],
            env={
                "CHIMERA_SOCKET_DIR": str(socket_dir),
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            },
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
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
        "    <key>RunAtLoad</key>\n    <true/>\n"
        "    <key>KeepAlive</key>\n    <true/>\n"
        "</dict>\n</plist>\n"
    )


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


def main(argv: list[str] | None = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.command == "shim-check":  # standalone diagnostic — needs no core config
        raise SystemExit(asyncio.run(_shim_check()))
    config = _config_from_env()
    if args.command == "status":
        raise SystemExit(asyncio.run(_status(config)))
    if args.command == "plist":
        print(launch_agent_plist(config.socket_dir))
        return
    if args.command == "up":
        asyncio.run(run_up(config))
        return
    config.socket_dir.mkdir(parents=True, exist_ok=True)
    asyncio.run(serve_forever(build_core(config)))


if __name__ == "__main__":
    main()
