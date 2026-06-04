"""Dual-role IPC client (§5.3, D0/D1) — observe-first slice.

ORACLE is the first module that is BOTH a producer-module and an event
consumer. Two UNIX connections coexist on one asyncio loop:

  #1 core.sock   (MODULE role)   — core.register, serve oracle.* via the 4A
                                    router, periodic core.heartbeat, and emit
                                    oracle.baseline.updated as a Notification.
                                    The writer is shared (responses + heartbeat
                                    + outbound events) -> guarded by an
                                    asyncio.Lock, mirroring server._push_loop.
  #2 events.sock (CONSUMER role) — core.subscribe to chaff.* (D5 allow-list),
                                    push-loop feeds each event to the Observer.

Reuses core.envelope (wire) + core.errors (codes) ONLY (D1=c).
TODO(D1): extract to chimera/modules/common/pyclient.py at the 2nd Python module.

advisory-only (D4): METHODS contains no acting method, and a module connection
cannot invoke another module's methods (core-side is_module guard). ORACLE only
answers its own oracle.* and listens.

STUB — RED slice. __init__ wires args; run() raises NotImplementedError, so the
daemon never registers (the integration tests stay red until GREEN).
"""

from pathlib import Path

from oracle.baseline import BaselineStore
from oracle.observer import Observer


class OracleClient:
    """ORACLE daemon's dual-role core client. STUB (RED slice)."""

    MODULE = "oracle"
    VERSION = "0.4.0-alpha"
    # observe-first: no oracle.classify yet (Ollama is a later slice, D8=c).
    METHODS: tuple[str, ...] = ("oracle.status", "oracle.observe")
    EVENTS: tuple[str, ...] = ("oracle.baseline.updated",)
    # D5=b: allow-list of real producers. MIRROR emits nothing yet, so only
    # CHAFF's two topics are subscribed for now.
    SUBSCRIBE_TOPICS: tuple[str, ...] = ("chaff.request.sent", "chaff.error")

    def __init__(
        self,
        socket_dir: Path,
        store: BaselineStore,
        *,
        baseline_every: int = 100,
        heartbeat_interval: float = 2.0,
    ) -> None:
        self._socket_dir = socket_dir
        self._store = store
        self._baseline_every = baseline_every
        self._heartbeat_interval = heartbeat_interval
        self._observer: Observer | None = None

    async def run(self) -> None:
        """Open both connections, register, serve + consume until cancelled."""
        raise NotImplementedError("OracleClient.run — RED slice")
