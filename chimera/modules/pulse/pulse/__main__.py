"""Daemon entry — `python -m pulse` (§5.5, daemon slice / PD-6).

Wires CoreConfig (socket_dir from CHIMERA_SOCKET_DIR), the encrypted BaselineStore, and
the module-only PulseClient, then runs the asyncio loop until SIGTERM/SIGINT, after which
the run task is cancelled and the store is closed.

Standalone run needs the `pulse` package importable (modules/pulse on sys.path):

    PYTHONPATH=chimera/modules/pulse python -m pulse

Daemon slice: registers + serves pulse.status / pulse.weights.set / enable / disable;
no live signal collection (MIRROR group-A, kqueue idle, ORACLE drift) — those are gated.
"""

import asyncio
import signal
from pathlib import Path

from core.config import CoreConfig

from pulse.baseline import BaselineStore
from pulse.client import PulseClient


async def _run(client: PulseClient) -> None:
    """Drive the client until SIGTERM/SIGINT cancels it."""
    loop = asyncio.get_running_loop()
    task = asyncio.ensure_future(client.run())
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, task.cancel)
    try:
        await task
    except asyncio.CancelledError:
        pass


def main() -> None:
    """Wire config + store + client (sync I/O), then run the asyncio loop."""
    config = CoreConfig()
    pulse_dir = Path("~/.config/chimera/pulse").expanduser()
    store = BaselineStore(pulse_dir / "baseline.db", pulse_dir / "baseline.key")
    client = PulseClient(
        config.socket_dir,
        store,
        heartbeat_interval=float(config.heartbeat_interval_s),
    )
    try:
        asyncio.run(_run(client))
    finally:
        store.close()


if __name__ == "__main__":
    main()
