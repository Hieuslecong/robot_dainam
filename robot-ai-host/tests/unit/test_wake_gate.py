"""Idle/active gate tests (spec 8.7) — decision logic, no pipeline runtime."""

from app.processors.wake_gate import WakeGate


def test_disabled_gate_always_active():
    gate = WakeGate(name="WakeGate", enabled=False)
    assert gate.active
    assert gate._admit()


def test_enabled_gate_boots_idle_and_drops():
    gate = WakeGate(name="WakeGate", enabled=True)
    assert not gate.active
    assert not gate._admit()


def test_wake_opens_gate():
    gate = WakeGate(name="WakeGate", enabled=True)
    gate.wake()
    assert gate._admit()


def test_timeout_returns_to_idle_and_clears_context():
    cleared = []
    gate = WakeGate(name="WakeGate", enabled=True, idle_timeout_seconds=0.5)
    gate.set_on_idle(lambda: cleared.append(True))
    gate.wake()
    gate._last_turn -= 1.0  # simulate silence past the timeout
    assert not gate._admit()
    assert cleared == [True]
    assert not gate.active


def test_sleep_noop_when_disabled():
    gate = WakeGate(name="WakeGate", enabled=False)
    gate.sleep()
    assert gate.active
