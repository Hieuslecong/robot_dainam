"""Tests for device-first worker lifecycle configuration."""

import inspect

import pytest

pytest.importorskip("pipecat", reason="Pipecat dependencies are unavailable in restricted audit environments")

from app.pipecat_runtime.worker_factory import create_worker_for_session


def test_worker_factory_disables_auto_intro_by_default():
    """Microphone test must wait for user speech instead of unsolicited bot audio."""
    signature = inspect.signature(create_worker_for_session)
    assert signature.parameters["auto_intro"].default is False
