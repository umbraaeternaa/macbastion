"""RED contract for Registry.mark_lost (CR-1, crash-restart). Fails against the
NotImplementedError stub; green once mark_lost lands.

A crashed module disconnects without a graceful core.deregister. mark_lost turns that
abrupt loss into a restartable FAILED state; a graceful deregister (STOPPED) is untouched.
"""

from core.broker import EventBroker
from core.config import CoreConfig
from core.lifecycle import Lifecycle, ModuleState
from core.registry import Registry


def _registry():
    broker = EventBroker()
    lifecycle = Lifecycle(CoreConfig.model_validate({}), broker)
    return Registry(lifecycle, broker), lifecycle


def test_mark_lost_live_module_to_failed():
    reg, lifecycle = _registry()
    reg.register("echo", "0", [], [])
    reg.mark_lost("echo")
    assert lifecycle.state_of("echo") == ModuleState.FAILED


def test_mark_lost_absent_is_noop():
    reg, _ = _registry()
    reg.mark_lost("ghost")  # no raise, no effect


def test_mark_lost_after_graceful_deregister_is_noop():
    reg, lifecycle = _registry()
    reg.register("echo", "0", [], [])
    reg.deregister("echo")  # graceful -> STOPPED, entry removed
    reg.mark_lost("echo")  # no-op: not registered anymore
    assert lifecycle.state_of("echo") == ModuleState.STOPPED
