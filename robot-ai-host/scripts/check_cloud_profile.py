#!/usr/bin/env python3
"""Validate and construct the cloud provider objects without making inference calls."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import get_settings, load_profile, validate_profile_runtime


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="google_vi")
    args = parser.parse_args()

    settings = get_settings()
    try:
        profile = load_profile(args.profile)
        validate_profile_runtime(profile, settings, require_credentials=True)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[FAIL] Cloud profile validation: {exc}")
        return 2

    try:
        from pipecat.services.google.stt import GoogleSTTService
        from pipecat.services.google.tts import GoogleTTSService
        from pipecat.services.openai.llm import OpenAILLMService
        from pipecat.services.tts_service import TextAggregationMode
        from pipecat.transcriptions.language import Language
    except ImportError as exc:
        print(f"[FAIL] Pipecat cloud dependencies are unavailable: {exc}")
        return 3

    stt = GoogleSTTService(
        credentials_path=settings.google_application_credentials,
        location=settings.google_location,
        settings=GoogleSTTService.Settings(
            languages=[Language.VI_VN],
            model=profile.stt.model or settings.google_stt_model,
            enable_interim_results=True,
            enable_automatic_punctuation=True,
        ),
        name="CloudProbeSTT",
    )
    llm = OpenAILLMService(
        api_key=settings.resolved_llm_api_key,
        base_url=settings.resolved_llm_base_url,
        default_headers=settings.llm_default_headers or None,
        retry_timeout_secs=settings.llm_timeout_seconds,
        retry_on_timeout=settings.llm_retry_on_timeout,
        settings=OpenAILLMService.Settings(
            model=profile.llm.model or settings.resolved_llm_model,
            system_instruction="Kiểm tra cấu hình; không gửi request.",
        ),
        name="CloudProbeLLM",
    )
    tts = GoogleTTSService(
        credentials_path=settings.google_application_credentials,
        location=None if settings.google_location == "global" else settings.google_location,
        text_aggregation_mode=TextAggregationMode.SENTENCE,
        settings=GoogleTTSService.Settings(
            voice=profile.tts.voice or settings.google_tts_voice,
            language=Language.VI_VN,
            speaking_rate=settings.google_tts_speaking_rate,
        ),
        name="CloudProbeTTS",
    )

    print(f"[PASS] profile={profile.name}")
    print(f"[PASS] credential_file={Path(settings.google_application_credentials).is_file()}")
    print(f"[PASS] STT={type(stt).__name__} model={profile.stt.model or settings.google_stt_model}")
    print(f"[PASS] LLM={type(llm).__name__} model={profile.llm.model or settings.resolved_llm_model}")
    print(f"[PASS] LLM base_url={settings.resolved_llm_base_url or 'OpenAI default'}")
    print(f"[PASS] TTS={type(tts).__name__} voice={profile.tts.voice or settings.google_tts_voice}")
    print("[PASS] Provider constructors completed without inference/network calls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
