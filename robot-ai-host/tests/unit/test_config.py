"""Configuration and profile validation tests."""

from pathlib import Path

import pytest

from app.config import (
    CONFIG_DIR,
    LEGACY_CONFIGS_DIR,
    PROFILES_PATH,
    Settings,
    load_profile,
    load_profiles,
    validate_profile_runtime,
)


def test_config_single_source_of_truth():
    """Phase 0 gate: config/ is the only runtime config directory."""
    assert CONFIG_DIR.name == "config"
    assert PROFILES_PATH == CONFIG_DIR / "profiles.yaml"
    assert PROFILES_PATH.is_file()
    assert (CONFIG_DIR / "assistant_school.yaml").is_file()
    assert not LEGACY_CONFIGS_DIR.exists(), "legacy configs/ must not reappear"


def test_legacy_configs_dir_fails_loudly(tmp_path, monkeypatch):
    """No silent fallback: a resurrected configs/ dir must abort profile loading."""
    import app.config as config_module

    monkeypatch.setattr(config_module, "LEGACY_CONFIGS_DIR", tmp_path / "configs")
    (tmp_path / "configs").mkdir()
    load_profiles.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="Ambiguous configuration"):
            load_profiles()
    finally:
        load_profiles.cache_clear()


def test_mock_profile_requires_no_cloud_credentials():
    settings = Settings(openai_api_key="", google_application_credentials="")
    validate_profile_runtime(load_profile("mock"), settings, require_credentials=True)


def test_google_profile_fails_fast_without_credentials():
    settings = Settings(
        openai_api_key="",
        google_application_credentials="",
        google_tts_voice="",
    )
    with pytest.raises(ValueError, match="GOOGLE_APPLICATION_CREDENTIALS"):
        validate_profile_runtime(load_profile("google_vi"), settings, require_credentials=True)


def test_google_profile_requires_vietnamese_voice(tmp_path: Path):
    credentials = tmp_path / "credentials.json"
    credentials.write_text("{}", encoding="utf-8")
    settings = Settings(
        openai_api_key="test-openai-key",
        google_application_credentials=str(credentials),
        google_tts_voice="",
    )
    with pytest.raises(ValueError, match="GOOGLE_TTS_VOICE"):
        validate_profile_runtime(load_profile("google_vi"), settings, require_credentials=True)


def test_google_profile_validates_with_all_required_values(tmp_path: Path):
    credentials = tmp_path / "credentials.json"
    credentials.write_text("{}", encoding="utf-8")
    settings = Settings(
        openai_api_key="test-openai-key",
        google_application_credentials=str(credentials),
        google_tts_voice="vi-VN-Chirp3-HD-Aoede",
        openai_model="gpt-4.1",
    )
    validate_profile_runtime(load_profile("google_vi"), settings, require_credentials=True)


def test_hybrid_profile_accepts_configurable_llm_and_requires_no_google_credentials():
    settings = Settings(
        llm_api_key="local-or-cloud-token",
        llm_base_url="http://127.0.0.1:11434/v1",
        llm_model="qwen2.5:7b",
        piper_base_url="http://127.0.0.1:5000",
        piper_voice="vi_VN-vais1000-medium",
        google_application_credentials="",
    )
    validate_profile_runtime(
        load_profile("hybrid_local_vi"), settings, require_credentials=True
    )
    assert settings.resolved_llm_api_key == "local-or-cloud-token"
    assert settings.resolved_llm_base_url == "http://127.0.0.1:11434/v1"
    assert settings.resolved_llm_model == "qwen2.5:7b"


def test_hybrid_profile_fails_without_llm_token():
    settings = Settings(
        llm_api_key="",
        openai_api_key="",
        llm_model="model",
        piper_base_url="http://127.0.0.1:5000",
    )
    with pytest.raises(ValueError, match="LLM_API_KEY"):
        validate_profile_runtime(
            load_profile("hybrid_local_vi"), settings, require_credentials=True
        )


def test_generic_llm_falls_back_to_legacy_openai_variables():
    settings = Settings(
        llm_api_key="",  # must be empty for legacy fallback to activate
        llm_model="",    # must be empty for legacy fallback to activate
        openai_api_key="legacy-token",
        openai_model="legacy-model",
    )
    assert settings.resolved_llm_api_key == "legacy-token"
    assert settings.resolved_llm_model == "legacy-model"


def test_llm_default_headers_json_is_typed():
    settings = Settings(llm_default_headers_json='{"X-Tenant": "robot-lab"}')
    assert settings.llm_default_headers == {"X-Tenant": "robot-lab"}


def test_llm_default_headers_json_rejects_non_string_values():
    settings = Settings(llm_default_headers_json='{"X-Retry": 3}')
    with pytest.raises(ValueError, match="JSON object of string values"):
        _ = settings.llm_default_headers
