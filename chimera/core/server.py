"""UNIX socket server — the core hub (§6.3 transport, §6.2 star, §6.9 auth).

The integrator. Server owns the two UNIX sockets, accepts connections, issues
per-connection capability tokens, and dispatches JSON-RPC commands by
composing the already-built core modules:

- envelope  — parse/serialize the NDJSON wire (§6.4)
- tokens    — issue on connect, validate per request (§6.9)
- registry  — core.register / core.deregister / core.capabilities (§6.7)
- lifecycle — core.heartbeat + the background liveness sweep (§7.4)
- broker    — core.subscribe fan-out + event push (§6.6)
- errors    — map every failure to a JSON-RPC error (§6.5)

Scope decisions (operator-approved, v0.2.0):
- D1 two sockets: core.sock (commands) + events.sock (events).
- D3 register-implies-module: a connection starts surface-scoped (full
  token); the first core.register reissues it module-scoped (sub=name).
- D4 core.* ONLY — any module.method returns -31000 module offline. There
  are no native modules yet, so there is nothing to route; this is an
  honest MVP, not a faked router (MANIFESTO §4). Routing lands with the
  first native module.
- D7 one asyncio task per connection; no connection cap.
- D8 graceful shutdown: stop accepting, close, unlink the socket files.

In 4B the token scope has no teeth yet (no module methods to forbid): the
token is validated only for core.* methods; a module method short-circuits
to -31000 before any auth check. A forged token on a core.* method -> -31007.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, ClassVar

from pydantic import ValidationError

from core.audit import AuditLog
from core.broker import Event, EventBroker, Subscription, SubscriptionClosedError
from core.config import CoreConfig
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
    JSONRPC_INVALID_REQUEST,
    JSONRPC_METHOD_NOT_FOUND,
    JSONRPC_PARSE_ERROR,
    ChimeraError,
    RpcError,
)
from core.gate import BLOCK, DELAY, decide
from core.lifecycle import InvalidTransitionError, Lifecycle
from core.override import OverrideStore
from core.registry import Registry
from core.shim_client import ShimClient, ShimError
from core.tier0 import run_tier0
from core.tokens import TokenIssuer

logger = logging.getLogger(__name__)


@dataclass
class Connection:
    """Per-connection session state.

    Mutable: the first core.register reissues the token module-scoped (3B),
    flipping subject/is_module. subscription holds the events.sock stream.
    """

    token: str
    subject: str
    is_module: bool = False
    subscription: Subscription | None = None


class Server:
    """The core hub: two UNIX sockets composing every other core module."""

    SURFACE_SUBJECT: ClassVar[str] = "surface"
    CORE_VERSION: ClassVar[str] = "0.2.0-alpha"
    CORE_METHODS: ClassVar[frozenset[str]] = frozenset(
        {
            "core.register",
            "core.heartbeat",
            "core.deregister",
            "core.capabilities",
            "core.status",
            "core.subscribe",
            "core.override.set",
            "core.lock",
            "core.purge",
        }
    )
    # Per-method routing deadlines (§6.8); anything else uses the config default.
    METHOD_TIMEOUTS: ClassVar[dict[str, float]] = {
        "vault.unlock": 10.0,
        "oracle.classify": 30.0,
        # oracle.ask: one LLM intent call; cold model load measured ~4.4s, so the
        # 5s default is too tight (NL-12a). 15s absorbs cold-load + IPC overhead.
        "oracle.ask": 15.0,
    }
    # Declarative anomaly-tripwire relay (idea #3, path B): when one of these event
    # topics is published, core — as authority, NOT a module — issues the mapped
    # command to the target module. Data, not logic; the D7 wire guard is untouched
    # (this path never originates from a connection). topic -> module.method.
    # topic -> the list of module.method reflexes core issues when it is published.
    # Fan-out: one event can drive several organs ("one mind"). Data, not logic; the
    # D7 wire guard is untouched (this path never originates from a connection).
    RELAY_RULES: ClassVar[dict[str, list[str]]] = {
        # A detected anomaly heightens TETHER's sensitivity, locks the vault, AND turns on
        # both obfuscation organs — the organism doesn't just defend, it obscures the
        # operator's real activity while the threat is live: CHAFF hides traffic *volume*
        # (decoy requests), ECHO hides traffic *timing* (constant-rate normalization).
        "oracle.anomaly.detected": [
            "tether.heighten", "vault.lock", "chaff.generation.start", "echo.start",
        ],
        # Losing the paired phone (TETHER dead-man) auto-locks the open vault — its
        # plaintext RAM mount is torn down (VD-9b). vault.lock with no params locks
        # whatever vault is currently open.
        "tether.absent": ["vault.lock"],
        # De-escalation — the threat has passed: the paired phone is back in range, so the
        # operator is present and the posture relaxes. Stand DOWN the obfuscation organs
        # that anomaly ramped up (the reflex web goes down, not only up). The vault is NOT
        # auto-unlocked — re-opening always requires a deliberate unlock (no auto-trust).
        "tether.recovered": ["chaff.generation.stop", "echo.stop"],
        # Symmetric stand-down on the MATCHING axis: ORACLE's all-clear (the anomaly score
        # crossed back down through the hysteresis band) relaxes the very obfuscation that
        # the anomaly raised. Same signal up, same signal down.
        "oracle.anomaly.cleared": ["chaff.generation.stop", "echo.stop"],
    }

    def __init__(
        self,
        config: CoreConfig,
        registry: Registry,
        lifecycle: Lifecycle,
        broker: EventBroker,
        token_issuer: TokenIssuer,
        override_store: OverrideStore | None = None,
        shim_client: ShimClient | None = None,
        audit_log: AuditLog | None = None,
    ) -> None:
        self._config = config
        self._registry = registry
        self._lifecycle = lifecycle
        self._broker = broker
        self._token_issuer = token_issuer
        self._override_store = override_store
        self._shim_client = shim_client
        # Reflex audit trail (AD-1): every reflex core actuates is recorded here, so the
        # operator can answer "why did my vault lock?" post-hoc. Always on — defaults to
        # audit.jsonl beside the sockets when not injected.
        self._audit_log = audit_log or AuditLog(config.socket_dir / "audit.jsonl")
        self._core_path = config.socket_dir / "core.sock"
        self._events_path = config.socket_dir / "events.sock"
        self._core_server: asyncio.Server | None = None
        self._events_server: asyncio.Server | None = None
        self._sweep_task: asyncio.Task[None] | None = None
        self._start_time: float | None = None
        self._next_sub_id: int = 0
        # Router 4A state.
        self._module_writers: dict[str, asyncio.StreamWriter] = {}
        self._pending: dict[int, tuple[asyncio.Future[Response], str]] = {}
        self._next_internal_id: int = 0
        # Anomaly-tripwire relay (idea #3, path B).
        self._relay_sub: Subscription | None = None
        self._relay_task: asyncio.Task[None] | None = None
        # Cognitive gate (PULSE-driven, GW-1): current mode + cached danger set.
        self._pulse_mode: str | None = None
        self._danger_set: set[str] = set()
        self._gate_sub: Subscription | None = None
        self._gate_task: asyncio.Task[None] | None = None
        self._refresh_task: asyncio.Task[None] | None = None
        # Dead-man actuation: react to TETHER's graduated escalation requests.
        self._escalation_sub: Subscription | None = None
        self._escalation_task: asyncio.Task[None] | None = None

    # -- connections ------------------------------------------------------

    def new_connection(self) -> Connection:
        """Open a session with a surface-scoped (full) capability token."""
        token = self._token_issuer.issue(
            self.SURFACE_SUBJECT, list(self.CORE_METHODS)
        )
        return Connection(token=token, subject=self.SURFACE_SUBJECT)

    # -- dispatch ---------------------------------------------------------

    async def handle_command(self, request: Request, conn: Connection) -> Response:
        """Authenticate (core.* only) and dispatch one request to a Response."""
        method = request.method
        try:
            if method in self.CORE_METHODS:
                self._token_issuer.validate(conn.token, method)
                if method == "core.lock":
                    result = await self._handle_lock()
                elif method == "core.purge":
                    result = await self._handle_purge()
                else:
                    result = self._dispatch_core(method, request.params, conn)
                return Response(jsonrpc="2.0", id=request.id, result=result)
            if method.startswith("core."):
                raise RpcError(code=JSONRPC_METHOD_NOT_FOUND)
            # 4A: forward the module method to the owning module's connection.
            return await self._route(request, conn)
        except Exception as exc:  # noqa: BLE001 — centralized wire mapping (D5)
            return self._to_error_response(exc, request.id)

    def _dispatch_core(
        self, method: str, params: dict[str, Any] | list[Any] | None, conn: Connection
    ) -> dict[str, Any]:
        if method == "core.register":
            return self._handle_register(params, conn)
        if method == "core.heartbeat":
            return self._handle_heartbeat(params)
        if method == "core.deregister":
            return self._handle_deregister(params)
        if method == "core.capabilities":
            return self._registry.capabilities()
        if method == "core.status":
            return self._handle_status()
        if method == "core.subscribe":
            return self._handle_subscribe(params, conn)
        if method == "core.override.set":
            return self._handle_override_set(params, conn)
        raise RpcError(code=JSONRPC_METHOD_NOT_FOUND)  # defensive

    # -- core.* handlers --------------------------------------------------

    async def _handle_lock(self) -> dict[str, Any]:
        """core.lock (operator command, §8.8) — ask the privileged shim to lock the screen."""
        if self._shim_client is None:
            raise RpcError(code=ChimeraError.PRECONDITION_FAILED, message="shim unavailable")
        try:
            return await self._shim_client.lock()
        except ShimError as exc:
            raise RpcError(code=ChimeraError.PRECONDITION_FAILED, message=str(exc)) from exc

    async def _handle_purge(self) -> dict[str, Any]:
        """core.purge (operator command, §5.8) — broadcast purge.imminent (modules zero their
        own keys), then run Tier-0: evict CHIMERA Keychain items via the shim + wipe the state
        DBs. Returns the Tier-0 report {keychain_evicted, state_files_removed, errors}."""
        if self._shim_client is None:
            raise RpcError(code=ChimeraError.PRECONDITION_FAILED, message="shim unavailable")
        self._broker.publish(Event(topic="purge.imminent", payload={}))
        return await run_tier0(self._shim_client, self._config.state_dir)

    def _handle_override_set(
        self, params: dict[str, Any] | list[Any] | None, conn: Connection
    ) -> dict[str, Any]:
        """Operator sets the gate-override phrase (OS-2).

        Surface-only — a module connection (even with a valid core token) is refused: the
        override phrase is the operator's, never a module's. Needs a configured store and a
        non-empty phrase. set_phrase does a ~100ms PBKDF2 — acceptable for a rare action.
        """
        if conn.is_module:
            raise RpcError(code=ChimeraError.NOT_AUTHORIZED)
        if self._override_store is None:
            raise RpcError(code=ChimeraError.PRECONDITION_FAILED)
        phrase = self._require_str(params, "phrase")
        if not phrase:
            raise RpcError(code=JSONRPC_INVALID_PARAMS, message="phrase must be non-empty")
        # GH-1: changing an existing phrase requires the correct current one (§8).
        current = params.get("current") if isinstance(params, dict) else None
        cur = current if isinstance(current, str) else None
        if not self._override_store.set_phrase(phrase, current=cur):
            raise RpcError(code=ChimeraError.NOT_AUTHORIZED)
        return {"ok": True}

    def _handle_register(
        self, params: dict[str, Any] | list[Any] | None, conn: Connection
    ) -> dict[str, Any]:
        module = self._require_str(params, "module")
        version = self._require_str(params, "version")
        methods = self._opt_list(params, "methods")
        events = self._opt_list(params, "events")
        depends_on = self._opt_list(params, "depends_on")
        self._registry.register(module, version, methods, events, depends_on)
        # 3B: this connection is now a module — reissue a module-scoped token.
        conn.subject = module
        conn.is_module = True
        conn.token = self._token_issuer.issue(module, list(self.CORE_METHODS))
        return {"ok": True}

    def _handle_heartbeat(
        self, params: dict[str, Any] | list[Any] | None
    ) -> dict[str, Any]:
        module = self._require_str(params, "module")
        try:
            self._lifecycle.heartbeat(module)
        except KeyError as e:
            raise RpcError(code=ChimeraError.MODULE_OFFLINE) from e
        return {"ok": True}

    def _handle_deregister(
        self, params: dict[str, Any] | list[Any] | None
    ) -> dict[str, Any]:
        module = self._require_str(params, "module")
        self._registry.deregister(module)  # idempotent — no-op if absent
        return {"ok": True}

    def _handle_status(self) -> dict[str, Any]:
        caps = self._registry.capabilities()
        modules: dict[str, Any] = {}
        for name, info in caps.items():
            rec = self._lifecycle.record(name)
            modules[name] = {
                **info,
                "last_seen": rec.last_seen,
                "restart_count": rec.restart_count,
            }
        uptime = (
            0.0
            if self._start_time is None
            else max(0.0, time.time() - self._start_time)
        )
        # Reactive state — the "one mind" made visible: the live PULSE cognitive mode and
        # the armed cross-module reflexes (data-driven RELAY_RULES + the two code reflexes).
        reflexes = [
            f"{topic} -> {', '.join(cmds)}" for topic, cmds in sorted(self.RELAY_RULES.items())
        ]
        reflexes.append("pulse:exhausted -> vault.lock")
        reflexes.append("tether.escalation L1/L2 -> shim.lock / vault.lock")
        return {
            "core": {"version": self.CORE_VERSION, "uptime_seconds": uptime},
            "modules": modules,
            "reactive": {"pulse_mode": self._pulse_mode or "normal", "reflexes": reflexes},
        }

    def _handle_subscribe(
        self, params: dict[str, Any] | list[Any] | None, conn: Connection
    ) -> dict[str, Any]:
        topics = self._opt_list(params, "topics")
        sub = self._broker.subscribe(topics)  # ValueError on empty -> -32602
        self._next_sub_id += 1
        conn.subscription = sub
        return {"subscription_id": self._next_sub_id}

    # -- router (4A): forward module.method to the owning module ----------

    def _timeout_for(self, method: str) -> float:
        """Routing deadline for a method: per-method override or config default."""
        return self.METHOD_TIMEOUTS.get(method, self._config.request_timeout_s)

    def _attach_module_writer(
        self, name: str, writer: asyncio.StreamWriter
    ) -> None:
        """Bind a module's live connection. Re-attach replaces the previous one."""
        if name in self._module_writers:
            self._detach_module_writer(name)
        self._module_writers[name] = writer

    def _detach_module_writer(self, name: str) -> None:
        """Drop a module's connection and fail its in-flight requests (-31000)."""
        self._module_writers.pop(name, None)
        offline = RpcError(code=ChimeraError.MODULE_OFFLINE).to_dict()
        for internal_id, (future, owner) in list(self._pending.items()):
            if owner == name and not future.done():
                future.set_result(
                    Response(jsonrpc="2.0", id=internal_id, error=offline)
                )

    def _resolve_pending(self, response: Response) -> None:
        """Deliver a module's reply to the waiting caller (ignore unknown ids)."""
        entry = self._pending.get(response.id) if isinstance(response.id, int) else None
        if entry is None:
            return
        future, _owner = entry
        if not future.done():
            future.set_result(response)

    async def _issue_to_module(
        self, method: str, params: dict[str, Any] | list[Any] | None
    ) -> Response:
        """Send a module method to its owner, await and return the raw reply.

        Shared plumbing for _route (operator-driven, behind the D7 guard) and
        _dispatch_internal (core-authority, in-process). Does the registry/writer
        checks, internal-id correlation, write, and bounded await — raising RpcError
        for an offline owner, a missing method, or a timeout. The returned Response
        keeps the internal correlation id; the caller maps it to its own context.
        """
        owner = method.split(".", 1)[0]
        if not self._registry.is_registered(owner):
            raise RpcError(code=ChimeraError.MODULE_OFFLINE)
        if not self._registry.has_method(method):
            raise RpcError(code=ChimeraError.CAPABILITY_MISSING)
        writer = self._module_writers.get(owner)
        if writer is None:  # registered but no live connection
            raise RpcError(code=ChimeraError.MODULE_OFFLINE)

        self._next_internal_id += 1
        internal_id = self._next_internal_id
        future: asyncio.Future[Response] = asyncio.get_running_loop().create_future()
        self._pending[internal_id] = (future, owner)
        forwarded = Request(
            jsonrpc="2.0",
            id=internal_id,
            method=method,
            params=params,
        )
        try:
            writer.write(serialize_frame(forwarded).encode())
            await writer.drain()
            return await asyncio.wait_for(future, self._timeout_for(method))
        except TimeoutError as e:
            raise RpcError(code=ChimeraError.MODULE_TIMEOUT) from e
        finally:
            self._pending.pop(internal_id, None)

    async def _route(self, request: Request, conn: Connection) -> Response:
        """Forward a module method to its module, await the reply, relay it back."""
        # D7: only surfaces may invoke module methods; a module may not.
        if conn.is_module:
            raise RpcError(code=ChimeraError.NOT_AUTHORIZED)
        await self._gate(request.method, request.params)  # GW-4/OV-3: friction + override
        forwarded = self._strip_override(request.params)
        reply = await self._issue_to_module(request.method, forwarded)
        # Rewrite the module's reply id back to the original caller's id.
        if reply.error is not None:
            return Response(jsonrpc="2.0", id=request.id, error=reply.error)
        return Response(jsonrpc="2.0", id=request.id, result=reply.result)

    # -- anomaly-tripwire relay (idea #3, path B) -------------------------

    async def _dispatch_internal(
        self, method: str, params: dict[str, Any] | None
    ) -> Response:
        """Issue a module command on core's OWN authority (no connection).

        The single core-initiated command path. It reuses _issue_to_module but is
        never reachable from the wire — no JSON-RPC method maps here, so the D7
        guard in _route (modules cannot invoke modules) is untouched. The raw reply
        is returned as-is: core has no external caller, so there is no caller-id
        rewrite. Raises RpcError on offline/timeout, which _relay_handle isolates.
        """
        return await self._issue_to_module(method, params)

    async def _relay_one(self, topic: str, target: str) -> None:
        """Issue one relay target on core's authority, isolating every failure mode.

        Every actuation is recorded to the audit trail (AD-1) with its outcome — ok or a
        short failure string — so the operator can review what the organism did and why.
        """
        try:
            reply = await self._dispatch_internal(target, None)
        except RpcError as exc:
            logger.warning("anomaly relay %s -> %s failed: %s", topic, target, exc)
            self._audit(topic, target, f"error: {exc}")
            return
        except Exception as exc:  # noqa: BLE001 — relay must never crash the consume loop
            logger.exception("anomaly relay %s -> %s raised", topic, target)
            self._audit(topic, target, f"error: {exc}")
            return
        if reply.error is not None:
            logger.warning(
                "anomaly relay %s -> %s returned error: %s", topic, target, reply.error
            )
            self._audit(topic, target, f"error: {reply.error.get('message', reply.error)}")
        else:
            logger.info("anomaly relay %s -> %s ok", topic, target)
            self._audit(topic, target, "ok")

    def _audit(self, topic: str, target: str, outcome: str) -> None:
        """Record one actuated reflex; a failing audit write must never break a reflex."""
        try:
            self._audit_log.record(topic=topic, commands=[target], outcome=outcome)
        except OSError:
            logger.exception("audit write failed for %s -> %s", topic, target)

    async def _relay_handle(self, event: Event) -> None:
        """Relay one broker event to ALL its mapped module commands (RELAY_RULES).

        Core acts as authority — it issues each command in-process, never via a
        connection, so the D7 wire guard is untouched. Fan-out: a topic may map to
        several reflexes, issued concurrently. Resilient: an unmapped topic issues
        nothing; each target's missing-module / timeout / error is isolated and
        logged, never raised, so the consume loop and the sibling reflexes survive.
        """
        targets = self.RELAY_RULES.get(event.topic)
        if not targets:
            return  # no rule for this topic — issue nothing
        await asyncio.gather(*(self._relay_one(event.topic, t) for t in targets))

    async def _relay_loop(self) -> None:
        """Consume relay-rule events and dispatch each (errors isolated per event)."""
        assert self._relay_sub is not None
        try:
            while True:
                event = await self._relay_sub.get()
                await self._relay_handle(event)
        except SubscriptionClosedError:
            return

    # -- cognitive gate (PULSE-driven, GW-1…GW-6) -------------------------

    async def _gate(
        self, method: str, params: dict[str, Any] | list[Any] | None
    ) -> None:
        """Apply PULSE-driven friction before forwarding a danger action (GW-4 / OV-3).

        A non-danger method (or an allow/confirm decision) returns and the forward
        proceeds; a tired mode delays; an exhausted mode raises DENIED_BY_POLICY (-31003)
        UNLESS the request carries a correct `_override` phrase (§8 — the operator can
        always proceed). confirm is forwarded — its dialog is the surface's job.
        """
        if method not in self._danger_set:
            return
        decision = decide(
            method, self._pulse_mode, self._danger_set,
            override_ok=self._override_ok(params),
        )
        if decision.decision == BLOCK:
            raise RpcError(code=ChimeraError.DENIED_BY_POLICY, message=decision.reason)
        if decision.decision == DELAY:
            await asyncio.sleep(decision.delay_seconds)

    def _override_ok(self, params: dict[str, Any] | list[Any] | None) -> bool:
        """True if the request carries a verified override phrase (OV-3)."""
        if self._override_store is None or not isinstance(params, dict):
            return False
        phrase = params.get("_override")
        return isinstance(phrase, str) and self._override_store.verify(phrase)

    @staticmethod
    def _strip_override(
        params: dict[str, Any] | list[Any] | None,
    ) -> dict[str, Any] | list[Any] | None:
        """Drop the `_override` secret before forwarding — modules never see it (OV-3)."""
        if isinstance(params, dict) and "_override" in params:
            return {k: v for k, v in params.items() if k != "_override"}
        return params

    async def _gate_loop(self) -> None:
        """Track PULSE's current mode from pulse.mode.changed events (GW-2)."""
        assert self._gate_sub is not None
        try:
            while True:
                event = await self._gate_sub.get()
                new_mode = event.payload.get("new_mode")
                if isinstance(new_mode, str):
                    await self._apply_pulse_mode(new_mode)
        except SubscriptionClosedError:
            return

    async def _apply_pulse_mode(self, new_mode: str) -> None:
        """Adopt PULSE's new mode (GW-2) and run the cognitive reflex (the "one mind"
        reacting to the OPERATOR): the transition INTO 'exhausted' — the operator is
        critically fatigued — auto-locks the vault, securing the data when the human is
        not sharp. Issued once per entry on core's authority (like the relay), errors
        isolated; lower-friction modes (caution/tired) are left to the gate, not a lock.
        """
        prev = self._pulse_mode
        self._pulse_mode = new_mode
        if new_mode == "exhausted" and prev != "exhausted":
            await self._relay_one("pulse.mode.changed", "vault.lock")

    async def _on_tether_escalation(self, event: Event) -> None:
        """Actuate TETHER's graduated dead-man escalation (EMIT-ONLY in TETHER — the
        Monitor only REQUESTS; core acts). L1 -> screen-lock via the privileged shim;
        L2 -> vault.lock; L3 (PURGE) is opt-in and is NEVER auto-run from a reflex.
        Each action is isolated so a failure never crashes the consume loop.
        """
        action = event.payload.get("action_requested")
        if action == "lock_screen":
            # Shim screen-lock bypasses _relay_one, so audit it here directly (AD-1).
            if self._shim_client is None:
                self._audit("tether.escalation", "shim.lock", "error: shim unavailable")
            else:
                try:
                    await self._shim_client.lock()
                except Exception as exc:  # noqa: BLE001 — reflex must never crash the loop
                    logger.exception("tether escalation: shim screen-lock failed")
                    self._audit("tether.escalation", "shim.lock", f"error: {exc}")
                else:
                    self._audit("tether.escalation", "shim.lock", "ok")
        elif action == "lock_vaults":
            await self._relay_one("tether.escalation", "vault.lock")
        elif action == "trigger_purge":
            # L3 is the nuclear option — irreversible. Auto-running it from a reflex is
            # unsafe; PURGE stays operator opt-in (core.purge), never an automatic effect.
            # A requested-but-refused PURGE is security-relevant — leave a trace (AD-1).
            logger.warning(
                "tether escalation requested PURGE (L3) — opt-in only, not auto-run"
            )
            self._audit("tether.escalation", "purge.trigger", "refused: L3 opt-in only")

    async def _escalation_loop(self) -> None:
        """Consume tether.escalation events and actuate each (errors isolated)."""
        assert self._escalation_sub is not None
        try:
            while True:
                event = await self._escalation_sub.get()
                await self._on_tether_escalation(event)
        except SubscriptionClosedError:
            return

    async def _refresh_danger(self) -> None:
        """Query pulse.danger.list and cache the danger set (GW-3).

        Core-authority query (no connection). Resilient: an offline PULSE, a timeout, a
        malformed reply, or any error leaves the previous set intact and is swallowed —
        the gate fails OPEN on a stale/empty set, never blocks on a refresh failure.
        """
        try:
            reply = await self._dispatch_internal("pulse.danger.list", None)
        except Exception:  # noqa: BLE001 — a refresh failure must never raise
            logger.exception("danger-set refresh failed")
            return
        if reply.error is not None or not isinstance(reply.result, dict):
            return
        registry = reply.result.get("registry")
        if isinstance(registry, list):
            self._danger_set = {str(s) for s in registry}

    # -- param helpers ----------------------------------------------------

    def _require_str(
        self, params: dict[str, Any] | list[Any] | None, key: str
    ) -> str:
        if not isinstance(params, dict) or key not in params:
            raise RpcError(code=JSONRPC_INVALID_PARAMS, message=f"missing param: {key}")
        value = params[key]
        if not isinstance(value, str):
            raise RpcError(code=JSONRPC_INVALID_PARAMS, message=f"param not a string: {key}")
        return value

    def _opt_list(
        self, params: dict[str, Any] | list[Any] | None, key: str
    ) -> list[Any]:
        if not isinstance(params, dict):
            return []
        value = params.get(key, [])
        if not isinstance(value, list):
            raise RpcError(code=JSONRPC_INVALID_PARAMS, message=f"param not a list: {key}")
        return value

    # -- error mapping (D5, §6.5) ----------------------------------------

    def _to_error_response(self, exc: Exception, req_id: int | str | None) -> Response:
        """Map any handler failure to a JSON-RPC error Response."""
        if isinstance(exc, RpcError):
            error = exc.to_dict()
        elif isinstance(exc, InvalidTransitionError):
            error = RpcError(code=ChimeraError.PRECONDITION_FAILED).to_dict()
        elif isinstance(exc, ValueError):
            error = RpcError(
                code=JSONRPC_INVALID_PARAMS, message=str(exc) or None
            ).to_dict()
        else:
            error = RpcError(code=JSONRPC_INTERNAL_ERROR).to_dict()
        return Response(jsonrpc="2.0", id=req_id, error=error)

    # -- transport lifecycle (D1, D8, D10) --------------------------------

    async def start(self) -> None:
        """Bind both sockets (0600 in a 0700 dir) and launch the sweep task."""
        socket_dir = self._config.socket_dir
        socket_dir.mkdir(parents=True, exist_ok=True)
        socket_dir.chmod(self._config.socket_dir_mode)
        for path in (self._core_path, self._events_path):
            path.unlink(missing_ok=True)  # clear a stale socket
        self._core_server = await asyncio.start_unix_server(
            self._serve_commands, path=str(self._core_path)
        )
        self._events_server = await asyncio.start_unix_server(
            self._serve_events, path=str(self._events_path)
        )
        self._core_path.chmod(self._config.socket_mode)
        self._events_path.chmod(self._config.socket_mode)
        self._start_time = time.time()
        self._sweep_task = asyncio.create_task(self._lifecycle.run())
        # Subscribe core itself to the relay-rule topics and consume them in a
        # dedicated task (mirrors the sweep task; errors isolated per event).
        if self.RELAY_RULES:
            self._relay_sub = self._broker.subscribe(list(self.RELAY_RULES))
            self._relay_task = asyncio.create_task(self._relay_loop())
        # GW-2: track PULSE's mode via pulse.mode.changed.
        self._gate_sub = self._broker.subscribe(["pulse.mode.changed"])
        self._gate_task = asyncio.create_task(self._gate_loop())
        # Dead-man actuation: react to TETHER's graduated escalation ladder.
        self._escalation_sub = self._broker.subscribe(["tether.escalation"])
        self._escalation_task = asyncio.create_task(self._escalation_loop())

    async def stop(self) -> None:
        """Stop accepting, close both sockets, unlink them, cancel the sweep."""
        if self._sweep_task is not None:
            self._sweep_task.cancel()
            try:
                await self._sweep_task
            except asyncio.CancelledError:
                pass
            self._sweep_task = None
        if self._relay_task is not None:
            self._relay_task.cancel()
            try:
                await self._relay_task
            except asyncio.CancelledError:
                pass
            self._relay_task = None
        if self._relay_sub is not None:
            self._relay_sub.close()
            self._relay_sub = None
        for task in (self._gate_task, self._refresh_task, self._escalation_task):
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._gate_task = None
        self._refresh_task = None
        self._escalation_task = None
        if self._gate_sub is not None:
            self._gate_sub.close()
            self._gate_sub = None
        if self._escalation_sub is not None:
            self._escalation_sub.close()
            self._escalation_sub = None
        for server in (self._core_server, self._events_server):
            if server is not None:
                server.close()
                await server.wait_closed()
        self._core_server = None
        self._events_server = None
        for path in (self._core_path, self._events_path):
            path.unlink(missing_ok=True)

    async def __aenter__(self) -> "Server":
        await self.start()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.stop()

    # -- connection handlers ---------------------------------------------

    async def _serve_commands(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        conn = self.new_connection()
        attached: str | None = None
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                response = await self._handle_line(line.decode(), conn)
                if response is not None:
                    writer.write(self._serialize_response(response).encode())
                    await writer.drain()
                # Once a module registers (is_module flips), bind its connection
                # so core can forward routed requests to it (4A).
                if conn.is_module and attached is None:
                    attached = conn.subject
                    self._attach_module_writer(attached, writer)
                    if attached == "pulse":  # GW-3: refresh the cached danger set
                        self._refresh_task = asyncio.create_task(self._refresh_danger())
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            if attached is not None:
                self._detach_module_writer(attached)
                # An abrupt disconnect (crash) -> FAILED so the supervisor restarts it; a
                # graceful core.deregister already moved it to STOPPED (mark_lost no-ops).
                self._registry.mark_lost(attached)
            await self._close_writer(writer)

    async def _serve_events(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        conn = self.new_connection()
        lock = asyncio.Lock()
        push_task: asyncio.Task[None] | None = None
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                response = await self._handle_line(line.decode(), conn)
                if response is not None:
                    async with lock:
                        writer.write(self._serialize_response(response).encode())
                        await writer.drain()
                if conn.subscription is not None and push_task is None:
                    push_task = asyncio.create_task(
                        self._push_loop(conn.subscription, writer, lock)
                    )
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            if push_task is not None:
                push_task.cancel()
            if conn.subscription is not None:
                conn.subscription.close()
            await self._close_writer(writer)

    async def _push_loop(
        self, sub: Subscription, writer: asyncio.StreamWriter, lock: asyncio.Lock
    ) -> None:
        """Stream a subscription's events to a client as Notification frames."""
        try:
            while True:
                event = await sub.get()
                note = Notification(
                    jsonrpc="2.0", method=event.topic, params=event.payload
                )
                async with lock:
                    writer.write(serialize_frame(note).encode())
                    await writer.drain()
        except (SubscriptionClosedError, ConnectionError):
            return

    async def _handle_line(self, line: str, conn: Connection) -> Response | None:
        """Parse one frame and dispatch. Returns None for inbound events."""
        try:
            message = parse_frame(line)
        except json.JSONDecodeError:
            return self._to_error_response(RpcError(code=JSONRPC_PARSE_ERROR), None)
        except (ValueError, ValidationError):
            return self._to_error_response(
                RpcError(code=JSONRPC_INVALID_REQUEST), None
            )
        if isinstance(message, Request):
            return await self.handle_command(message, conn)
        if isinstance(message, Response):
            # A module replying to a routed request (4A correlation).
            self._resolve_pending(message)
            return None
        if isinstance(message, Notification):
            payload = message.params if isinstance(message.params, dict) else {}
            self._broker.publish(Event(topic=message.method, payload=payload))
        return None

    # -- serialization ----------------------------------------------------

    def _serialize_response(self, response: Response) -> str:
        """Serialize a Response frame, keeping the id present even when null.

        envelope.serialize drops None via exclude_none, but JSON-RPC requires
        the id field (null for parse errors), so re-add it explicitly.
        """
        data = response.model_dump(exclude_none=True)
        data.setdefault("id", response.id)
        return json.dumps(data, separators=(",", ":")) + "\n"

    @staticmethod
    async def _close_writer(writer: asyncio.StreamWriter) -> None:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, BrokenPipeError):
            pass
