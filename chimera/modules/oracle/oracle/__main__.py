"""Daemon entry — `python -m oracle` (§5.3).

Wires CoreConfig (socket_dir from CHIMERA_SOCKET_DIR via env_prefix), the
encrypted BaselineStore, and the dual-role OracleClient, then runs the asyncio
loop until SIGTERM/SIGINT, after which the run task is cancelled and the store
is closed.

Standalone-run path (flagged tail from RED): `python -m oracle` requires the
`oracle` package to be importable, i.e. modules/oracle on sys.path. Run it as:

    PYTHONPATH=chimera/modules/oracle python -m oracle

(or from within chimera/modules/oracle). A proper editable install of the
package is a follow-up; __main__ cannot self-fix this — to import oracle.__main__
the package must already be on the path.

observe-first: no Ollama, no classify, no Mode B (later slice).
"""

import asyncio
import os
import signal
from pathlib import Path

from core.config import CoreConfig

from oracle.baseline import BaselineStore
from oracle.client import OracleClient
from oracle.detector import Detector
from oracle.llm import LlmClient

DEFAULT_BASELINE_EVERY = 100


async def _run(client: OracleClient) -> None:
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
    oracle_dir = Path("~/.config/chimera/oracle").expanduser()
    store = BaselineStore(oracle_dir / "baseline.db", oracle_dir / "baseline.key")
    # Mode B: wire the LLM detector so oracle.classify works live (local Ollama). Default
    # model qwen2.5:7b — it calibrates threat scores reliably (the 1B model under/over-scored);
    # CHIMERA_ORACLE_MODEL overrides. Ollama down -> classify fails per-call, not at startup.
    model = os.environ.get("CHIMERA_ORACLE_MODEL", "qwen2.5:7b")
    detector = Detector(LlmClient(model=model), store)
    client = OracleClient(
        config.socket_dir,
        store,
        detector=detector,
        baseline_every=DEFAULT_BASELINE_EVERY,
        heartbeat_interval=float(config.heartbeat_interval_s),
    )
    try:
        asyncio.run(_run(client))
    finally:
        store.close()


if __name__ == "__main__":
    main()
