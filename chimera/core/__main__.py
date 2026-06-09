"""CHIMERA core entry point — run via `python -m core` (SV-1).

Wires and runs the unprivileged core: socket server, router, broker, registry, token
issuer, and the override store. In production launchd (a LaunchAgent) is the real
supervisor that launches and watches this process (§7.10); module daemons are brought
up separately (the SV-2 supervisor). This module is just "what launchd runs".
"""

from __future__ import annotations

import asyncio
import os
import signal
from pathlib import Path

from core.broker import EventBroker
from core.config import CoreConfig
from core.lifecycle import Lifecycle
from core.override import OverrideStore
from core.registry import Registry
from core.server import Server
from core.tokens import TokenIssuer


def build_core(config: CoreConfig) -> Server:
    """Construct a fully-wired (but not yet started) core Server from config."""
    broker = EventBroker()
    lifecycle = Lifecycle(config, broker)
    registry = Registry(lifecycle, broker)
    override = OverrideStore(config.socket_dir / "override.json")
    return Server(config, registry, lifecycle, broker, TokenIssuer(), override_store=override)


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


def main() -> None:
    config = _config_from_env()
    config.socket_dir.mkdir(parents=True, exist_ok=True)
    asyncio.run(serve_forever(build_core(config)))


if __name__ == "__main__":
    main()
