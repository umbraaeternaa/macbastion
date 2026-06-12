"""PULSE daemon core client (§5.5, daemon slice / PD-1…PD-9).

Module-only client (PD-1): ONE core.sock connection that registers with core, serves
pulse.* via the 4A router, and heartbeats — mirroring ORACLE's command connection.
PULSE's group-A (MIRROR aggregates) and group-C (ORACLE drift) consumers are gated, so
there is no events.sock consumer this slice.

pulse.status composes the live edge (PD-3): temporal_signal(now) feeds the empty
`temporal` slot of assess(store, …) -> (score, mode). advisory only, fail-OPEN — an
uncalibrated store yields baseline_ready=False -> mode 'normal' (§8). Reuses
core.envelope + core.errors only (D1=c; extract a shared pyclient at the 2nd Python
module — same TODO as ORACLE). pulse.mode.changed/error are registered but not yet
emitted (PD-4, status is pull-based).
"""

from __future__ import annotations

import asyncio
import math
import re
import subprocess
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from core.envelope import Notification, Request, Response, parse_frame, serialize_frame
from core.errors import (
    JSONRPC_INTERNAL_ERROR,
    JSONRPC_INVALID_PARAMS,
    JSONRPC_METHOD_NOT_FOUND,
    ChimeraError,
    RpcError,
)

from pulse.assess import assess
from pulse.baseline import BaselineStore
from pulse.idle import IdleTracker
from pulse.registry import DangerRegistry
from pulse.scoring import Weights
from pulse.temporal import temporal_signal

_HID_IDLE_RE = re.compile(r'"HIDIdleTime"\s*=\s*(\d+)')


def _read_system_idle_seconds() -> float | None:
    """Current HID idle seconds via `ioreg -c IOHIDSystem` (HIDIdleTime is ns since the
    last input event). Manual-tier — live on macOS. Any failure -> None (fail-open §8:
    a broken idle sensor must never inflate fatigue / lock the operator out)."""
    try:
        out = subprocess.run(
            ["/usr/sbin/ioreg", "-c", "IOHIDSystem"],
            capture_output=True, text=True, timeout=2.0, check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    match = _HID_IDLE_RE.search(out)
    if match is None:
        return None
    return int(match.group(1)) / 1_000_000_000.0  # ns -> s


class _DisconnectError(Exception):
    """Raised inside the connection loop when core closes the socket (EOF)."""


class PulseClient:
    """PULSE daemon's core client (module role)."""

    MODULE = "pulse"
    VERSION = "0.1.0-alpha"
    METHODS: tuple[str, ...] = (
        "pulse.status",
        "pulse.weights.set",
        "pulse.enable",
        "pulse.disable",
        "pulse.danger.add",
        "pulse.danger.remove",
        "pulse.danger.list",
        "pulse.calibrate.start",
        "pulse.calibrate.reset",
    )
    EVENTS: tuple[str, ...] = ("pulse.mode.changed", "pulse.error")

    def __init__(
        self,
        socket_dir: Path,
        store: BaselineStore,
        *,
        session_start: str | None = None,
        chronotype: str = "typical",
        weights: Weights | None = None,
        danger_registry: DangerRegistry | None = None,
        heartbeat_interval: float = 2.0,
        tick_interval: float = 60.0,
        idle_reader: Callable[[], float | None] | None = None,
    ) -> None:
        self._socket_dir = Path(socket_dir)
        self._store = store
        self._session_start = session_start
        self._chronotype = chronotype
        self._weights = weights if weights is not None else Weights()
        self._danger_registry = danger_registry
        # group-B live idle producer: read system idle each tick, track gap-ends (PD-idle-2)
        self._idle_reader = idle_reader if idle_reader is not None else _read_system_idle_seconds
        self._idle = IdleTracker()
        self._heartbeat_interval = heartbeat_interval
        self._tick_interval = tick_interval
        self._enabled = True
        self._cmd_writer: asyncio.StreamWriter | None = None
        self._cmd_lock = asyncio.Lock()
        self._registered = asyncio.Event()
        self._req_id = 0
        self._last_mode: str | None = None  # EM-2: emit pulse.mode.changed on transition

    @property
    def _core_sock(self) -> Path:
        return self._socket_dir / "core.sock"

    # -- lifecycle --------------------------------------------------------

    async def run(self) -> None:
        """Open core.sock, register, serve pulse.* + heartbeat until dropped."""
        if self._session_start is None:
            self._session_start = datetime.now().isoformat()
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._serve_command_conn())
                tg.create_task(self._heartbeat_loop())
                tg.create_task(self._tick_loop())
        except* _DisconnectError:
            pass  # core closed the socket — graceful exit
        except* (ConnectionError, OSError, asyncio.IncompleteReadError):
            pass  # transport gone — graceful exit

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

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
        try:
            message = parse_frame(line)
        except Exception:  # noqa: BLE001 — tolerate a malformed frame
            return
        if isinstance(message, Request):
            await self._send_cmd(await self._dispatch(message))

    async def _dispatch(self, request: Request) -> Response:
        try:
            if request.method == "pulse.status":
                result = await self._handle_status()
            elif request.method == "pulse.weights.set":
                result = self._handle_weights_set(request.params)
            elif request.method == "pulse.enable":
                result = self._handle_enable()
            elif request.method == "pulse.disable":
                result = self._handle_disable()
            elif request.method == "pulse.danger.add":
                result = self._handle_danger_add(request.params)
            elif request.method == "pulse.danger.remove":
                result = self._handle_danger_remove(request.params)
            elif request.method == "pulse.danger.list":
                result = self._handle_danger_list()
            elif request.method == "pulse.calibrate.start":
                result = await self._handle_calibrate_start()
            elif request.method == "pulse.calibrate.reset":
                result = await self._handle_calibrate_reset()
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

    # -- handlers ---------------------------------------------------------

    async def _compute(self, now: str) -> tuple[float, str, str]:
        """Advisory composition (EM-1): temporal_signal -> assess over the store.

        Returns (score, mode, primary_signal). primary is 'temporal' — the only present
        group this slice (group A/C gated). The idle sub-signal is live (PD-idle-2): read
        system idle, feed the tracker, pass its last_idle_end into temporal.
        """
        idle_seconds = await asyncio.to_thread(self._idle_reader)
        if idle_seconds is not None:
            self._idle.observe(now, idle_seconds)
        temporal = temporal_signal(
            now, session_start=self._session_start,
            last_idle_end=self._idle.last_idle_end,
            chronotype=self._chronotype,
        )
        score, mode = await asyncio.to_thread(
            assess, self._store, now, group_a=None, temporal=temporal,
            drift=None, weights=self._weights,
        )
        return score, mode, "temporal"

    async def _handle_status(self) -> dict[str, Any]:
        """Advisory state (PD-3): temporal_signal -> assess over the store."""
        now = datetime.now().isoformat()
        score, mode, _ = await self._compute(now)
        baseline_ready = await asyncio.to_thread(self._store.baseline_ready, now)
        return {
            "score": score,
            "mode": mode,
            "baseline_ready": baseline_ready,
            "session_minutes": self._session_minutes(now),
            "enabled": self._enabled,
        }

    def _session_minutes(self, now: str) -> int:
        if self._session_start is None:
            return 0
        delta = datetime.fromisoformat(now) - datetime.fromisoformat(self._session_start)
        return max(0, int(delta.total_seconds() // 60))

    def _handle_weights_set(
        self, params: dict[str, Any] | list[Any] | None
    ) -> dict[str, Any]:
        if not isinstance(params, dict):
            raise RpcError(code=JSONRPC_INVALID_PARAMS, message="params must be object")
        try:
            w_a, w_b, w_c = float(params["w_a"]), float(params["w_b"]), float(params["w_c"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RpcError(code=JSONRPC_INVALID_PARAMS, message="w_a/w_b/w_c required") from exc
        if not math.isclose(w_a + w_b + w_c, 1.0, abs_tol=1e-9):
            raise RpcError(code=JSONRPC_INVALID_PARAMS, message="weights must sum to 1.0")
        self._weights = Weights(w_a=w_a, w_b=w_b, w_c=w_c)
        return {"config": {"w_a": w_a, "w_b": w_b, "w_c": w_c}}

    def _handle_enable(self) -> dict[str, Any]:
        self._enabled = True
        return {"ok": True, "enabled": True}

    def _handle_disable(self) -> dict[str, Any]:
        self._enabled = False
        return {"ok": True, "enabled": False}

    def _danger_sig(self, params: dict[str, Any] | list[Any] | None) -> str:
        sig = params.get("action_signature") if isinstance(params, dict) else None
        if not isinstance(sig, str):
            raise RpcError(code=JSONRPC_INVALID_PARAMS, message="action_signature required")
        return sig

    def _handle_danger_list(self) -> dict[str, Any]:
        if self._danger_registry is None:
            raise RpcError(code=ChimeraError.PRECONDITION_FAILED)
        return {"registry": self._danger_registry.list()}

    def _handle_danger_add(
        self, params: dict[str, Any] | list[Any] | None
    ) -> dict[str, Any]:
        if self._danger_registry is None:
            raise RpcError(code=ChimeraError.PRECONDITION_FAILED)
        return {"registry": self._danger_registry.add(self._danger_sig(params))}

    def _handle_danger_remove(
        self, params: dict[str, Any] | list[Any] | None
    ) -> dict[str, Any]:
        if self._danger_registry is None:
            raise RpcError(code=ChimeraError.PRECONDITION_FAILED)
        return {"registry": self._danger_registry.remove(self._danger_sig(params))}

    async def _handle_calibrate_start(self) -> dict[str, Any]:
        """Report calibration progress; stamp the epoch on first call (PF-3).

        Calibration is passive — the store accrues buckets as signals arrive. start just
        reports progress and records WHEN calibration began (idempotent; re-stamps after a
        reset cleared it).
        """
        now = datetime.now().isoformat()
        days = await asyncio.to_thread(self._store.calibration_days, now)
        ready = await asyncio.to_thread(self._store.baseline_ready, now)
        started = await asyncio.to_thread(self._store.get_meta, "calibration_started_at")
        if not started:
            started = now
            await asyncio.to_thread(self._store.set_meta, "calibration_started_at", now)
        return {
            "days_observed": days,
            "days_required": self._store.CALIBRATION_DAYS,
            "ready": ready,
            "started_at": started,
        }

    async def _handle_calibrate_reset(self) -> dict[str, Any]:
        """Wipe the baseline to recalibrate from scratch (PF-4) — operator-invoked."""
        await asyncio.to_thread(self._store.clear)
        await asyncio.to_thread(self._store.set_meta, "calibration_started_at", "")
        return {"ok": True, "days_observed": 0}

    async def _safe_tick(self, now: str) -> None:
        """Run one tick; on ANY error emit pulse.error and continue (PF-5).

        The tick loop must never die (fail-open §8); an internal failure is announced as
        an advisory pulse.error, not raised.
        """
        try:
            await self._tick(now)
        except Exception as exc:  # noqa: BLE001 — announce, never let the loop die
            await self._send_cmd(
                Notification(
                    jsonrpc="2.0",
                    method="pulse.error",
                    params={"where": "tick", "message": str(exc)},
                )
            )

    async def _tick(self, now: str) -> None:
        """Compute the current mode; emit pulse.mode.changed on a transition (EM-2).

        The first tick establishes _last_mode (no emit); later ticks emit only when the
        mode actually changes — advisory (announce, not act); core relays (§5).
        """
        score, mode, primary = await self._compute(now)
        if self._last_mode is not None and mode != self._last_mode:
            await self._send_cmd(
                Notification(
                    jsonrpc="2.0",
                    method="pulse.mode.changed",
                    params={
                        "old_mode": self._last_mode,
                        "new_mode": mode,
                        "score": score,
                        "primary_signal": primary,
                    },
                )
            )
        self._last_mode = mode

    async def _tick_loop(self) -> None:
        await self._registered.wait()
        while True:
            await asyncio.sleep(self._tick_interval)
            await self._safe_tick(datetime.now().isoformat())

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

    async def _send_cmd(self, message: Request | Response | Notification) -> None:
        if self._cmd_writer is None:
            return
        async with self._cmd_lock:
            self._cmd_writer.write(serialize_frame(message).encode())
            await self._cmd_writer.drain()

    @staticmethod
    async def _close_writer(writer: asyncio.StreamWriter) -> None:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, BrokenPipeError):
            pass
