"""Source-level contracts that remain runnable without optional local models."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_pipeline_uses_configurable_llm_endpoint_and_token():
    source = (ROOT / "app/pipecat_runtime/pipeline_factory.py").read_text(encoding="utf-8")
    assert "base_url=settings.resolved_llm_base_url" in source
    assert "api_key=settings.resolved_llm_api_key" in source
    assert "model=profile.llm.model or settings.resolved_llm_model" in source


def test_hybrid_pipeline_uses_official_whisper_and_piper_services():
    source = (ROOT / "app/pipecat_runtime/pipeline_factory.py").read_text(encoding="utf-8")
    assert "WhisperSTTServiceMLX" in source
    assert "WhisperSTTService" in source
    assert "PiperHttpTTSService" in source
    assert "TextAggregationMode.SENTENCE" in source


def test_hybrid_installers_pin_pipecat_and_piper():
    mac = (ROOT / "scripts/install_hybrid_macos.sh").read_text(encoding="utf-8")
    linux = (ROOT / "scripts/install_hybrid_linux.sh").read_text(encoding="utf-8")
    for source in (mac, linux):
        assert "pipecat-ai[" in source
        assert "==1.6.0" in source
        assert 'PIPER_VERSION="${PIPER_VERSION:-1.5.0}"' in source
