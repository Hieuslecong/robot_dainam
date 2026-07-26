#!/usr/bin/env python3
"""Validate Hybrid profile without sending an LLM request or loading Whisper by default."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import get_settings, load_profile, validate_profile_runtime


async def _check_piper(base_url: str, timeout_seconds: float) -> tuple[bool, str]:
    try:
        import aiohttp
    except ImportError as exc:
        return False, f"aiohttp unavailable: {exc}"

    timeout = aiohttp.ClientTimeout(total=min(timeout_seconds, 5.0))
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Piper HTTP server primarily accepts POST. A 400/405 still proves
            # that the expected local HTTP service is reachable.
            async with session.get(base_url) as response:
                if response.status < 500:
                    return True, f"reachable (HTTP {response.status})"
                return False, f"server error (HTTP {response.status})"
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="hybrid_local_vi")
    parser.add_argument("--skip-piper-health", action="store_true")
    parser.add_argument(
        "--load-stt",
        action="store_true",
        help="Instantiate/download the selected Whisper model (can be slow).",
    )
    args = parser.parse_args()

    settings = get_settings()
    try:
        profile = load_profile(args.profile)
        validate_profile_runtime(profile, settings, require_credentials=True)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[FAIL] Hybrid profile validation: {exc}")
        return 2

    try:
        from pipecat.services.openai.llm import OpenAILLMService
        from pipecat.services.piper.tts import PiperHttpTTSService
    except ImportError as exc:
        print(f"[FAIL] Base Pipecat dependencies unavailable: {exc}")
        return 3

    try:
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
            name="HybridProbeLLM",
        )
    except Exception as exc:
        print(f"[FAIL] LLM constructor: {exc}")
        return 4

    if args.load_stt:
        try:
            from app.pipecat_runtime.pipeline_factory import _create_local_whisper_stt

            stt = _create_local_whisper_stt(settings=settings, profile=profile)
            print(f"[PASS] STT loaded: {type(stt).__name__}")
        except Exception as exc:
            print(f"[FAIL] Local STT load: {exc}")
            return 5
    else:
        backend = settings.resolved_local_stt_backend
        try:
            from pipecat.services.whisper import stt as _whisper_module  # noqa: F401
        except ImportError as exc:
            print(f"[FAIL] Whisper dependencies for backend={backend}: {exc}")
            return 5
        print(f"[PASS] Whisper imports available: backend={backend}")

    if not args.skip_piper_health:
        ok, detail = asyncio.run(
            _check_piper(settings.piper_base_url, settings.piper_request_timeout_seconds)
        )
        if not ok:
            print(f"[FAIL] Piper endpoint {settings.piper_base_url}: {detail}")
            return 6
        print(f"[PASS] Piper endpoint: {detail}")

    print(f"[PASS] profile={profile.name}")
    print(f"[PASS] LLM service={type(llm).__name__}")
    print(f"[PASS] LLM base_url={settings.resolved_llm_base_url or 'OpenAI default'}")
    print(f"[PASS] LLM model={profile.llm.model or settings.resolved_llm_model}")
    print("[PASS] LLM token configured (value intentionally hidden)")
    print(f"[PASS] Piper voice={profile.tts.voice or settings.piper_voice}")
    print("[PASS] No inference request was sent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
