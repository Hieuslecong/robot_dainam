"""Typed application and provider-profile configuration."""

from __future__ import annotations

import json
import platform
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent
# Single configuration source of truth. The legacy ``configs/`` directory was
# removed in the Phase 0 cleanup; loading must fail loudly if it reappears to
# avoid silent divergence between two config trees.
CONFIG_DIR = ROOT_DIR / "config"
PROFILES_PATH = CONFIG_DIR / "profiles.yaml"
LEGACY_CONFIGS_DIR = ROOT_DIR / "configs"


class ProviderProfile(BaseModel):
    """Provider selection and optional provider settings."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    streaming: bool = False
    model: str | None = None
    voice: str | None = None
    aggregation: Literal["sentence", "token"] | None = None


class TurnProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vad: Literal["silero", "none"] = "silero"
    smart_turn: bool = False


class RuntimeProfile(BaseModel):
    """Validated voice runtime profile."""

    model_config = ConfigDict(extra="forbid")

    name: str
    language: str = "vi-VN"
    transport: Literal["webrtc"] = "webrtc"
    stt: ProviderProfile
    llm: ProviderProfile
    tts: ProviderProfile
    turn: TurnProfile = Field(default_factory=TurnProfile)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        if value != "vi-VN":
            raise ValueError("MVP currently supports only vi-VN")
        return value


class Settings(BaseSettings):
    """Server configuration loaded from environment and ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8000
    max_sessions: int = 4
    provisioning_secret: str = "change-me-in-production"
    jwt_secret_key: str = "change-me-in-production"
    jwt_expiry_seconds: int = 3600
    heartbeat_timeout_seconds: int = 30
    log_level: str = "INFO"
    default_profile: str = "mock"
    cors_origins: str = "http://127.0.0.1:8000,http://localhost:8000"

    # Mock test harness.
    mock_auto_transcribe: bool = True
    mock_scripted_transcripts: str = (
        "Xin chào, tôi là người dùng thử nghiệm|"
        "Tên tôi là Minh Hiếu|"
        "Tôi vừa nói tên gì"
    )

    # Generic OpenAI-compatible LLM configuration. These values are used by
    # both ``google_vi`` and ``hybrid_local_vi``. Legacy OPENAI_* variables are
    # retained as fallbacks for existing deployments.
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
    llm_default_headers_json: str = "{}"
    llm_timeout_seconds: float = 30.0
    llm_retry_on_timeout: bool = True
    # Spec 9.6: conversation temperature 0.45–0.6. Router/planner get their own
    # values when adaptive routing lands (Phase 3).
    llm_temperature: float = 0.5
    llm_max_tokens: int = 160
    llm_stream: bool = True
    llm_runtime_hint: str = "unknown"
    # Spec 9.1 optional role models; empty falls back to LLM_MODEL.
    llm_router_model: str = ""
    llm_executor_model: str = ""
    llm_planner_model: str = ""

    # Assistant profile
    assistant_profile: str = "config/assistant_school.yaml"
    # Persona name is a branding decision pending school confirmation (spec 9.4).
    # It must stay configurable and never be hard-coded in source.
    persona_name: str = "Trợ lý AI của trường"
    # Hard overflow ceiling per response (everyday brevity comes from the
    # prompt; long-form like storytelling stays legal under this cap).
    response_max_sentences: int = 8
    response_max_words: int = 150
    # Spec 13.1: keep the last 6–8 turns verbatim; older turns are summarized.
    conversation_max_turns: int = 8

    # Device policy
    device_policy: str = "auto"
    pytorch_device: str = "auto"
    allow_cpu_fallback: bool = True
    log_device_diagnostics: bool = True

    # Backward-compatible aliases used by earlier project versions.
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1"

    # Google Cloud provider configuration for the optional google_vi profile.
    google_application_credentials: str = ""
    google_location: str = "global"
    google_stt_model: str = "latest_long"
    google_tts_voice: str = ""
    google_tts_speaking_rate: float = 1.0

    # Local Whisper STT. ``auto`` chooses MLX on Apple Silicon and
    # Faster-Whisper elsewhere.
    local_stt_backend: Literal["auto", "mlx", "faster-whisper"] = "auto"
    # Spec 8.1: select one of the five candidates in config/stt_candidates.yaml
    # by name (e.g. STT_CANDIDATE=stt_balanced_vi). Empty = legacy model vars.
    stt_candidate: str = ""
    whisper_mlx_model: str = "mlx-community/whisper-large-v3-turbo-q4"
    whisper_model: str = "deepdml/faster-whisper-large-v3-turbo-ct2"
    whisper_device: str = "auto"
    whisper_compute_type: str = "default"
    whisper_no_speech_prob: float = 0.6
    whisper_temperature: float = 0.0

    # Silero VAD tuning (spec 8.5). Defaults match Pipecat defaults; tune with
    # real recordings, not by feel.
    vad_confidence: float = 0.7
    vad_start_secs: float = 0.2
    vad_stop_secs: float = 0.8
    vad_min_volume: float = 0.6

    # Idle/active gate for public spaces (spec 8.7). Disabled for browser dev;
    # robot deployments enable it and wake via button/touch (RTVI robot.wake).
    wake_mode_enabled: bool = False
    idle_timeout_seconds: float = 30.0

    # Glossary correction (spec 8.3).
    glossary_enabled: bool = True

    # Two-tier TTS (spec 16.2a): Piper opener + VieNeu expressive tier.
    # Off by default until the VieNeu smoke test passes on this hardware.
    tts_two_tier_enabled: bool = False
    # True = spec 16.2a latency mask (sentence 1 Piper, rest VieNeu — two voices
    # in one reply). False = single VieNeu voice for the whole reply; first
    # audio arrives later but the voice never switches mid-answer.
    tts_opener_first: bool = False
    # Max wait for the first VieNeu sentence when tts_opener_first is False.
    tts_expressive_first_sentence_timeout_seconds: float = 8.0
    # VieNeu preset voice name (e.g. "Trúc Ly"). Empty → SDK default preset.
    vieneu_voice: str = ""
    # Playback speed factor applied to VieNeu output: >1.0 raises BOTH pitch
    # and tempo (younger, more energetic timbre). Sensible range 1.0–1.12.
    vieneu_speed: float = 1.0
    # Sampling temperature for VieNeu (default SDK 0.8). Higher → livelier,
    # more varied prosody; too high risks mispronunciation.
    vieneu_temperature: float = 0.8
    # Native codec streaming: first audio ~0.5s instead of full-sentence render.
    # Kill-switch: set false to fall back to per-sentence rendering.
    vieneu_streaming: bool = True
    # Expression style for VieNeu rendering (spec 15.2 allowlist). Per-turn
    # dynamic style is future work; this sets the session-wide base style.
    vieneu_style: str = "friendly"

    # Piper local HTTP sidecar.
    piper_base_url: str = "http://127.0.0.1:5000"
    piper_voice: str = "vi_VN-vais1000-medium"
    piper_request_timeout_seconds: float = 20.0
    local_stt_max_sessions: int = 1

    # Observability.
    metrics_jsonl_path: str = "artifacts/runtime-metrics.jsonl"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def scripted_transcripts(self) -> list[str]:
        return [item.strip() for item in self.mock_scripted_transcripts.split("|") if item.strip()]

    @property
    def resolved_llm_api_key(self) -> str:
        return (self.llm_api_key or self.openai_api_key).strip()

    @property
    def resolved_llm_model(self) -> str:
        return (self.llm_model or self.openai_model).strip()

    @property
    def resolved_llm_base_url(self) -> str | None:
        value = self.llm_base_url.strip()
        return value.rstrip("/") if value else None

    @property
    def llm_default_headers(self) -> dict[str, str]:
        raw = self.llm_default_headers_json.strip() or "{}"
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM_DEFAULT_HEADERS_JSON must be valid JSON") from exc
        if not isinstance(value, dict) or not all(
            isinstance(key, str) and isinstance(item, str) for key, item in value.items()
        ):
            raise ValueError("LLM_DEFAULT_HEADERS_JSON must be a JSON object of string values")
        return value

    @property
    def resolved_local_stt_backend(self) -> Literal["mlx", "faster-whisper"]:
        if self.local_stt_backend == "mlx":
            return "mlx"
        if self.local_stt_backend == "faster-whisper":
            return "faster-whisper"
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            return "mlx"
        return "faster-whisper"


@lru_cache
def get_settings() -> Settings:
    return Settings()


STT_CANDIDATES_PATH = CONFIG_DIR / "stt_candidates.yaml"


class STTCandidate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    engine: Literal["mlx", "faster_whisper", "sherpa_onnx"]
    model: str


@lru_cache
def load_stt_candidates() -> dict[str, STTCandidate]:
    if not STT_CANDIDATES_PATH.exists():
        raise FileNotFoundError(f"STT candidates config not found: {STT_CANDIDATES_PATH}")
    with STT_CANDIDATES_PATH.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return {name: STTCandidate.model_validate(value) for name, value in raw.items()}


def resolve_stt_candidate(settings: Settings) -> STTCandidate | None:
    """Return the selected STT candidate, or None for legacy model vars."""
    name = settings.stt_candidate.strip()
    if not name:
        return None
    candidates = load_stt_candidates()
    if name not in candidates:
        raise ValueError(f"Unknown STT_CANDIDATE: {name}. Available: {sorted(candidates)}")
    return candidates[name]


@lru_cache
def load_profiles() -> dict[str, RuntimeProfile]:
    if LEGACY_CONFIGS_DIR.exists():
        raise RuntimeError(
            "Ambiguous configuration: legacy 'configs/' directory exists alongside "
            "'config/'. 'config/' is the only runtime source; delete 'configs/'."
        )
    if not PROFILES_PATH.exists():
        raise FileNotFoundError(f"Profile config not found: {PROFILES_PATH}")
    with PROFILES_PATH.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict) or not raw:
        raise ValueError("config/profiles.yaml must contain at least one profile")
    return {name: RuntimeProfile.model_validate(value) for name, value in raw.items()}


def load_profile(profile_name: str) -> RuntimeProfile:
    profiles = load_profiles()
    try:
        return profiles[profile_name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown profile: {profile_name}. Available: {sorted(profiles)}"
        ) from exc


def _validate_llm(profile: RuntimeProfile, settings: Settings, *, require_credentials: bool) -> None:
    if profile.llm.provider not in {"openai", "openai_compatible"}:
        return
    if require_credentials and not settings.resolved_llm_api_key:
        raise ValueError("LLM_API_KEY (or legacy OPENAI_API_KEY) is required")
    if not (profile.llm.model or settings.resolved_llm_model).strip():
        raise ValueError("LLM_MODEL (or legacy OPENAI_MODEL) must not be empty")
    if settings.llm_timeout_seconds <= 0:
        raise ValueError("LLM_TIMEOUT_SECONDS must be greater than zero")
    # Parse now so malformed custom headers fail before WebRTC negotiation.
    settings.llm_default_headers


def validate_profile_runtime(
    profile: RuntimeProfile,
    settings: Settings,
    *,
    require_credentials: bool = True,
) -> None:
    """Fail fast before WebRTC negotiation for invalid profile configuration."""

    if profile.transport != "webrtc":
        raise ValueError(f"Unsupported transport: {profile.transport}")

    supported = {
        "stt": {"mock", "google", "whisper_local"},
        "llm": {"mock", "openai", "openai_compatible"},
        "tts": {"mock", "google", "piper_http"},
    }
    for kind, provider in (
        ("stt", profile.stt.provider),
        ("llm", profile.llm.provider),
        ("tts", profile.tts.provider),
    ):
        if provider not in supported[kind]:
            raise ValueError(f"Unsupported {kind.upper()} provider: {provider}")

    if profile.name == "mock":
        return

    if profile.tts.aggregation not in (None, "sentence"):
        raise ValueError("MVP requires sentence-level TTS aggregation")

    if profile.stt.provider == "google" or profile.tts.provider == "google":
        credential_path = Path(settings.google_application_credentials).expanduser()
        if require_credentials and not settings.google_application_credentials:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS is required for google_vi")
        if require_credentials and not credential_path.is_file():
            raise ValueError(
                "GOOGLE_APPLICATION_CREDENTIALS does not point to a readable file"
            )

    if profile.tts.provider == "google":
        voice = (profile.tts.voice or settings.google_tts_voice).strip()
        if not voice:
            raise ValueError("GOOGLE_TTS_VOICE must be set to a Vietnamese voice")
        if not voice.startswith("vi-VN-"):
            raise ValueError("GOOGLE_TTS_VOICE must start with vi-VN-")
        if "Chirp3-HD" not in voice and "Journey" not in voice:
            raise ValueError(
                "Google streaming TTS requires a supported Chirp3-HD or Journey voice"
            )

    if profile.stt.provider == "google" and not (
        profile.stt.model or settings.google_stt_model
    ).strip():
        raise ValueError("GOOGLE_STT_MODEL must not be empty")

    _validate_llm(profile, settings, require_credentials=require_credentials)

    if profile.stt.provider == "whisper_local":
        if settings.resolved_local_stt_backend == "mlx":
            model = profile.stt.model or settings.whisper_mlx_model
        else:
            model = profile.stt.model or settings.whisper_model
        if not model.strip():
            raise ValueError("A local Whisper model must be configured")
        if not 0.0 <= settings.whisper_no_speech_prob <= 1.0:
            raise ValueError("WHISPER_NO_SPEECH_PROB must be between 0 and 1")

    if profile.tts.provider == "piper_http":
        if not settings.piper_base_url.startswith(("http://", "https://")):
            raise ValueError("PIPER_BASE_URL must be an HTTP(S) URL")
        voice = (profile.tts.voice or settings.piper_voice).strip()
        if not voice:
            raise ValueError("PIPER_VOICE must not be empty")
        if settings.piper_request_timeout_seconds <= 0:
            raise ValueError("PIPER_REQUEST_TIMEOUT_SECONDS must be greater than zero")
