"""Dual-role IPC client (§5.3, D0/D1) — observe-first slice.

ORACLE is the first module that is BOTH a producer-module and an event
consumer. Two UNIX connections coexist on one asyncio loop, run as sibling
tasks under an asyncio.TaskGroup:

  #1 core.sock   (MODULE role)   — core.register, serve oracle.* via the 4A
                                    router, periodic core.heartbeat, and emit
                                    oracle.baseline.updated as a Notification.
                                    The writer is shared (responses + heartbeat
                                    + outbound events) -> guarded by an
                                    asyncio.Lock, mirroring server._push_loop.
  #2 events.sock (CONSUMER role) — core.subscribe to chaff.* (D5 allow-list),
                                    push-loop feeds each event to the Observer.

If any connection drops (core gone), its loop raises _DisconnectError; the TaskGroup
cancels the siblings and run() returns — a graceful exit (no supervisor yet).

Reuses core.envelope (wire) + core.errors (codes) ONLY (D1=c).
TODO(D1): extract to chimera/modules/common/pyclient.py at the 2nd Python module.

advisory-only (D4): METHODS contains no acting method, and a module connection
cannot invoke another module's methods (core-side is_module guard). ORACLE only
answers its own oracle.* and listens.
"""

import asyncio
from pathlib import Path
from typing import Any

from core.envelope import (
    Notification,
    Request,
    Response,
    parse_frame,
    serialize_frame,
)
from core.errors import (
    JSONRPC_INTERNAL_ERROR,
    JSONRPC_INVALID_PARAMS,
    JSONRPC_METHOD_NOT_FOUND,
    ChimeraError,
    RpcError,
)

from oracle.baseline import BaselineStore
from oracle.detector import Detector
from oracle.observer import Observer


class _DisconnectError(Exception):
    """Raised inside a connection loop when core closes the socket (EOF)."""


class OracleClient:
    """ORACLE daemon's dual-role core client (§5.3)."""

    MODULE = "oracle"
    VERSION = "0.4.0-alpha"
    # Mode B slice adds classify + threshold.set (manual-only, MD-B-2a/MD-B-8a).
    METHODS: tuple[str, ...] = (
        "oracle.status",
        "oracle.observe",
        "oracle.classify",
        "oracle.threshold.set",
    )
    EVENTS: tuple[str, ...] = ("oracle.baseline.updated", "oracle.error")
    # D5=b: allow-list of real producers. MIRROR emits nothing yet, so only
    # CHAFF's two topics are subscribed for now.
    SUBSCRIBE_TOPICS: tuple[str, ...] = ("chaff.request.sent", "chaff.error")

    def __init__(
        self,
        socket_dir: Path,
        store: BaselineStore,
        *,
        detector: Detector | None = None,
        baseline_every: int = 100,
        heartbeat_interval: float = 2.0,
    ) -> None:
        self._socket_dir = Path(socket_dir)
        self._store = store
        self._detector = detector  # DI (MD-B-1); None -> classify gated -31004
        self._heartbeat_interval = heartbeat_interval
        self._observer = Observer(
            store,
            baseline_every=baseline_every,
            on_baseline_updated=self._emit_baseline_updated,
        )
        self._cmd_writer: asyncio.StreamWriter | None = None
        self._cmd_lock = asyncio.Lock()
        self._registered = asyncio.Event()
        self._req_id = 0
        self._model = "unavailable"  # set by the startup probe (D6 / MD-B-6c)
        self._classifications_today = 0  # in-memory, approximate (no day-rollover)

    @property
    def _core_sock(self) -> Path:
        return self._socket_dir / "core.sock"

    @property
    def _events_sock(self) -> Path:
        return self._socket_dir / "events.sock"

    # -- lifecycle --------------------------------------------------------

    async def run(self) -> None:
        """Open both connections and serve + consume until cancelled/dropped."""
        await self._probe_model()
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._serve_command_conn())
                tg.create_task(self._consume_events_conn())
                tg.create_task(self._heartbeat_loop())
        except* _DisconnectError:
            pass  # core closed a socket — graceful exit
        except* (ConnectionError, OSError, asyncio.IncompleteReadError):
            pass  # transport gone — graceful exit

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def _probe_model(self) -> None:
        """D6 startup probe: cache the model name (or 'unavailable').

        Best-effort — a detector without an `llm` (e.g. a test fake) stays
        'unavailable'. Mode A never depends on this.
        """
        llm = getattr(self._detector, "llm", None)
        if llm is None:
            self._model = "unavailable"
            return
        available = await asyncio.to_thread(llm.available)
        self._model = str(llm.model) if available else "unavailable"

    # -- connection #1: core.sock (module role) ---------------------------

    async def _serve_command_conn(self) -> None:
        reader, writer = await asyncio.open_unix_connection(str(self._core_sock))
        self._cmd_writer = writer
        try:
            await self._send_cmd(
                Request(
                    jsonrpc="2.0",
                    id=self._next_id(),
                    method="core.register",
                    params={
                        "module": self.MODULE,
                        "version": self.VERSION,
                        "methods": list(self.METHODS),
                        "events": list(self.EVENTS),
                        "depends_on": [],
                    },
                )
            )
            self._registered.set()
            while True:
                line = await reader.readline()
                if not line:
                    raise _DisconnectError
                await self._on_command_frame(line.decode())
        finally:
            await self._close_writer(writer)
            self._cmd_writer = None

    async def _on_command_frame(self, line: str) -> None:
        """Dispatch one inbound frame on core.sock.

        Requests are routed oracle.* calls (4A) -> reply with a Response.
        Responses are acks to our own core.* calls -> ignore.
        """
        try:
            message = parse_frame(line)
        except Exception:  # noqa: BLE001 — tolerate a malformed frame
            return
        if isinstance(message, Request):
            response = await self._dispatch(message)
            await self._send_cmd(response)

    async def _dispatch(self, request: Request) -> Response:
        try:
            if request.method == "oracle.status":
                result = await self._handle_status()
            elif request.method == "oracle.observe":
                result = await self._handle_observe(request.params)
            elif request.method == "oracle.classify":
                result = await self._handle_classify(request.params)
            elif request.method == "oracle.threshold.set":
                result = await self._handle_threshold_set(request.params)
            else:
                raise RpcError(code=JSONRPC_METHOD_NOT_FOUND)
            return Response(jsonrpc="2.0", id=request.id, result=result)
        except RpcError as exc:
            return Response(jsonrpc="2.0", id=request.id, error=exc.to_dict())
        except Exception:  # noqa: BLE001 — never let a handler kill the loop
            return Response(
                jsonrpc="2.0",
                id=request.id,
                error=RpcError(code=JSONRPC_INTERNAL_ERROR).to_dict(),
            )

    async def _handle_status(self) -> dict[str, Any]:
        count = await asyncio.to_thread(self._store.event_count)
        return {
            "observing": True,
            "event_count": count,
            "baseline_events": count,
            "model": self._model,  # from the startup probe (D6 / MD-B-6c)
            "classifications_today": self._classifications_today,  # approximate
        }

    async def _handle_observe(
        self, params: dict[str, Any] | list[Any] | None
    ) -> dict[str, Any]:
        """Manual feed path: push one event into the baseline (§5 oracle.observe)."""
        if not isinstance(params, dict):
            raise RpcError(code=JSONRPC_INVALID_PARAMS, message="params must be object")
        source = params.get("source")
        event_type = params.get("event_type")
        if not isinstance(source, str) or not isinstance(event_type, str):
            raise RpcError(code=JSONRPC_INVALID_PARAMS, message="source/event_type required")
        payload = params.get("payload", {})
        if not isinstance(payload, dict):
            raise RpcError(code=JSONRPC_INVALID_PARAMS, message="payload must be object")
        await self._observer.record(f"{source}.{event_type}", payload)
        return {"ok": True}

    async def _handle_classify(
        self, params: dict[str, Any] | list[Any] | None
    ) -> dict[str, Any]:
        """Mode B (§5 oracle.classify): one-shot LLM classify (advisory).

        Gated (D6): no detector / Ollama down -> -31004. Returns {score,
        reasoning} only — no anomaly emission this slice (MD-B-7b).
        """
        if self._detector is None:
            raise RpcError(code=ChimeraError.PRECONDITION_FAILED)
        if not isinstance(params, dict) or not isinstance(params.get("event"), dict):
            raise RpcError(code=JSONRPC_INVALID_PARAMS, message="event object required")
        result = await self._detector.classify(params["event"])
        self._classifications_today += 1
        return result

    async def _handle_threshold_set(
        self, params: dict[str, Any] | list[Any] | None
    ) -> dict[str, Any]:
        """Mode B (§5 oracle.threshold.set): persist the anomaly threshold."""
        if self._detector is None:
            raise RpcError(code=ChimeraError.PRECONDITION_FAILED)
        if not isinstance(params, dict) or not isinstance(
            params.get("threshold"), int | float
        ):
            raise RpcError(code=JSONRPC_INVALID_PARAMS, message="threshold number required")
        return self._detector.set_threshold(float(params["threshold"]))

    async def _heartbeat_loop(self) -> None:
        await self._registered.wait()
        while True:
            await asyncio.sleep(self._heartbeat_interval)
            await self._send_cmd(
                Request(
                    jsonrpc="2.0",
                    id=self._next_id(),
                    method="core.heartbeat",
                    params={"module": self.MODULE},
                )
            )

    async def _emit_baseline_updated(self, payload: dict[str, Any]) -> None:
        """Observer callback: emit oracle.baseline.updated on core.sock (locked)."""
        await self._send_cmd(
            Notification(
                jsonrpc="2.0", method="oracle.baseline.updated", params=payload
            )
        )

    async def _send_cmd(self, message: Request | Response | Notification) -> None:
        """Write one frame to the shared command writer under the lock."""
        if self._cmd_writer is None:
            return
        async with self._cmd_lock:
            self._cmd_writer.write(serialize_frame(message).encode())
            await self._cmd_writer.drain()

    # -- connection #2: events.sock (consumer role) -----------------------

    async def _consume_events_conn(self) -> None:
        reader, writer = await asyncio.open_unix_connection(str(self._events_sock))
        try:
            writer.write(
                serialize_frame(
                    Request(
                        jsonrpc="2.0",
                        id=self._next_id(),
                        method="core.subscribe",
                        params={"topics": list(self.SUBSCRIBE_TOPICS)},
                    )
                ).encode()
            )
            await writer.drain()
            while True:
                line = await reader.readline()
                if not line:
                    raise _DisconnectError
                await self._on_event_frame(line.decode())
        finally:
            await self._close_writer(writer)

    async def _on_event_frame(self, line: str) -> None:
        """Feed a pushed Notification into the Observer; ignore the sub ack."""
        try:
            message = parse_frame(line)
        except Exception:  # noqa: BLE001 — tolerate a malformed frame
            return
        if isinstance(message, Notification):
            payload = message.params if isinstance(message.params, dict) else {}
            await self._observer.record(message.method, payload)

    @staticmethod
    async def _close_writer(writer: asyncio.StreamWriter) -> None:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, BrokenPipeError):
            pass
