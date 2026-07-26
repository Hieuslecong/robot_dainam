"""Create one isolated Pipecat pipeline per device session."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.services.tts_service import TextAggregationMode
from pipecat.transports.base_transport import BaseTransport

from app.config import RuntimeProfile, Settings
from app.core.context_manager import ContextManager
from app.core.system_prompt import build_system_prompt
from app.logging_utils import get_logger
from app.pipecat_runtime.providers import MockLLMService, MockTTSService, make_mock_stt
from app.pipecat_runtime.text_filter import VietnameseSpeechTextFilter
from app.processors.context_compactor import ContextCompactor
from app.processors.stt_guard import STTGuard
from app.processors.stream_deduplicator import StreamDeduplicator
from app.processors.response_policy import ResponsePolicyProcessor
from app.processors.small_talk_bypass import SmallTalkBypassProcessor
from app.processors.turn_grounding import TurnGroundingProcessor

logger = get_logger(__name__)


class AsyncClosable(Protocol):
    async def close(self) -> Any: ...


@dataclass
class PipelineBundle:
    pipeline: Pipeline
    context: LLMContext
    stt: object
    llm: object
    tts: object
    context_manager: ContextManager = field(default_factory=ContextManager)
    resources: list[AsyncClosable] = field(default_factory=list)
    wake_gate: object | None = None

    def reset_conversation(self) -> None:
        """Drop all conversation history, keeping only the system head."""
        self.context.set_messages(
            self.context_manager.reset(list(self.context.messages))
        )

    async def aclose(self) -> None:
        resources, self.resources = self.resources, []
        for resource in reversed(resources):
            try:
                await resource.close()
            except Exception as exc:
                logger.warning("pipeline_resource_close_failed", error=str(exc))


def _build_aggregators(context: LLMContext, settings: Settings | None = None):
    if settings is None:
        analyzer = SileroVADAnalyzer()
    else:
        from pipecat.audio.vad.vad_analyzer import VADParams

        analyzer = SileroVADAnalyzer(
            params=VADParams(
                confidence=settings.vad_confidence,
                start_secs=settings.vad_start_secs,
                stop_secs=settings.vad_stop_secs,
                min_volume=settings.vad_min_volume,
            )
        )
    return LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=analyzer),
    )


def _build_context_guard(context: LLMContext, settings: Settings):
    manager = ContextManager(max_recent_turns=settings.conversation_max_turns)
    compactor = ContextCompactor(context, manager, name="ContextCompactor")
    return manager, compactor


def _build_stt_guard(settings: Settings) -> STTGuard:
    glossary = None
    if settings.glossary_enabled:
        try:
            from app.core.glossary import GlossaryCorrector

            glossary = GlossaryCorrector()
        except Exception as exc:
            logger.warning("glossary_load_failed", error=str(exc))
    return STTGuard(name="STTGuard", glossary=glossary)


def _build_wake_gate(settings: Settings, on_idle) -> "WakeGate":
    from app.processors.wake_gate import WakeGate

    return WakeGate(
        enabled=settings.wake_mode_enabled,
        idle_timeout_seconds=settings.idle_timeout_seconds,
        on_idle=on_idle,
        name="WakeGate",
    )


def _create_openai_compatible_llm(
    *, settings: Settings, profile: RuntimeProfile, name: str
):
    """Create an OpenAI-compatible streaming LLM with configurable endpoint/token."""
    from pipecat.services.openai.llm import OpenAILLMService

    system_prompt = build_system_prompt(
        persona_name=settings.persona_name,
        llm_model=profile.llm.model or settings.resolved_llm_model,
        llm_endpoint=settings.resolved_llm_base_url or "",
    )

    return OpenAILLMService(
        api_key=settings.resolved_llm_api_key,
        base_url=settings.resolved_llm_base_url,
        default_headers=settings.llm_default_headers or None,
        retry_timeout_secs=settings.llm_timeout_seconds,
        retry_on_timeout=settings.llm_retry_on_timeout,
        settings=OpenAILLMService.Settings(
            model=profile.llm.model or settings.resolved_llm_model,
            system_instruction=system_prompt,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        ),
        name=name,
    )


def _create_mock_pipeline(
    transport: BaseTransport,
    *,
    settings: Settings,
) -> PipelineBundle:
    stt = make_mock_stt(settings.scripted_transcripts)
    llm = MockLLMService(name="MockLLM")
    tts = MockTTSService(
        name="MockSentenceToneTTS", text_filters=[VietnameseSpeechTextFilter()]
    )

    context = LLMContext()
    system_prompt = build_system_prompt(persona_name=settings.persona_name)
    context.add_message({"role": "system", "content": system_prompt})
    user_aggregator, assistant_aggregator = _build_aggregators(context, settings)

    stt_guard = _build_stt_guard(settings)
    wake_gate = _build_wake_gate(settings, on_idle=None)
    manager, compactor = _build_context_guard(context, settings)

    return PipelineBundle(
        pipeline=Pipeline(
            [
                transport.input(),
                stt,
                stt_guard,
                wake_gate,
                user_aggregator,
                compactor,
                llm,
                tts,
                transport.output(),
                assistant_aggregator,
            ]
        ),
        context=context,
        stt=stt,
        llm=llm,
        tts=tts,
        context_manager=manager,
        wake_gate=wake_gate,
    )


def _create_google_vi_pipeline(
    transport: BaseTransport,
    *,
    settings: Settings,
    profile: RuntimeProfile,
) -> PipelineBundle:
    from pipecat.services.google.stt import GoogleSTTService
    from pipecat.services.google.tts import GoogleTTSService
    from pipecat.transcriptions.language import Language

    stt = GoogleSTTService(
        credentials_path=settings.google_application_credentials,
        location=settings.google_location,
        settings=GoogleSTTService.Settings(
            languages=[Language.VI_VN],
            model=profile.stt.model or settings.google_stt_model,
            enable_automatic_punctuation=True,
            enable_interim_results=True,
            enable_voice_activity_events=False,
        ),
        name="GoogleVietnameseSTT",
    )

    llm = _create_openai_compatible_llm(
        settings=settings, profile=profile, name="ConfigurableVietnameseLLM"
    )

    tts = GoogleTTSService(
        credentials_path=settings.google_application_credentials,
        location=None if settings.google_location == "global" else settings.google_location,
        text_aggregation_mode=TextAggregationMode.SENTENCE,
        text_filters=[VietnameseSpeechTextFilter(strip_tags=True)],
        settings=GoogleTTSService.Settings(
            voice=profile.tts.voice or settings.google_tts_voice,
            language=Language.VI_VN,
            speaking_rate=settings.google_tts_speaking_rate,
        ),
        name="GoogleVietnameseStreamingTTS",
    )

    context = LLMContext()
    user_aggregator, assistant_aggregator = _build_aggregators(context, settings)
    stt_guard = _build_stt_guard(settings)
    wake_gate = _build_wake_gate(settings, on_idle=None)
    manager, compactor = _build_context_guard(context, settings)
    grounding = TurnGroundingProcessor(context, name="TurnGrounding")
    small_talk = SmallTalkBypassProcessor(
        context, persona_name=settings.persona_name, name="SmallTalkBypass"
    )
    dedup = StreamDeduplicator(name="StreamDedup")
    resp_policy = ResponsePolicyProcessor(
        max_sentences=settings.response_max_sentences,
        max_words=settings.response_max_words,
        name="ResponsePolicy",
    )

    return PipelineBundle(
        pipeline=Pipeline(
            [
                transport.input(),
                stt,
                stt_guard,
                wake_gate,
                user_aggregator,
                compactor,
                grounding,
                small_talk,
                llm,
                dedup,
                resp_policy,
                tts,
                transport.output(),
                assistant_aggregator,
            ]
        ),
        context=context,
        stt=stt,
        llm=llm,
        tts=tts,
        context_manager=manager,
        wake_gate=wake_gate,
    )


def _create_local_whisper_stt(*, settings: Settings, profile: RuntimeProfile):
    """Create the Pipecat local Whisper service selected for this host."""
    try:
        from pipecat.services.whisper.stt import WhisperSTTService, WhisperSTTServiceMLX
        from pipecat.transcriptions.language import Language
    except ImportError as exc:
        backend = settings.resolved_local_stt_backend
        if backend == "mlx":
            install = 'scripts/install_hybrid_macos.sh (requires both "whisper" and "mlx-whisper" extras)'
        else:
            install = "scripts/install_hybrid_linux.sh"
        raise RuntimeError(
            f"Local Whisper dependencies are unavailable for backend={backend}; run {install}"
        ) from exc

    from app.config import resolve_stt_candidate

    candidate = resolve_stt_candidate(settings)
    if candidate is not None:
        if candidate.engine == "sherpa_onnx":
            # Round-1 winner (report 02): WER 9.39%, decode P50 0.088 s.
            from app.pipecat_runtime.sherpa_stt import SherpaSTTService

            return SherpaSTTService(
                model_repo=candidate.model, name="LocalVietnameseSherpaSTT"
            )
        if candidate.engine == "faster_whisper":
            return WhisperSTTService(
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
                settings=WhisperSTTService.Settings(
                    model=candidate.model,
                    language=Language.VI,
                    no_speech_prob=settings.whisper_no_speech_prob,
                ),
                name="LocalVietnameseFasterWhisper",
            )
        return WhisperSTTServiceMLX(
            settings=WhisperSTTServiceMLX.Settings(
                model=candidate.model,
                language=Language.VI,
                no_speech_prob=settings.whisper_no_speech_prob,
                temperature=settings.whisper_temperature,
            ),
            name="LocalVietnameseWhisperMLX",
        )

    if settings.resolved_local_stt_backend == "mlx":
        return WhisperSTTServiceMLX(
            settings=WhisperSTTServiceMLX.Settings(
                model=profile.stt.model or settings.whisper_mlx_model,
                language=Language.VI,
                no_speech_prob=settings.whisper_no_speech_prob,
                temperature=settings.whisper_temperature,
            ),
            name="LocalVietnameseWhisperMLX",
        )

    return WhisperSTTService(
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
        settings=WhisperSTTService.Settings(
            model=profile.stt.model or settings.whisper_model,
            language=Language.VI,
            no_speech_prob=settings.whisper_no_speech_prob,
        ),
        name="LocalVietnameseFasterWhisper",
    )


async def _create_hybrid_local_vi_pipeline(
    transport: BaseTransport,
    *,
    settings: Settings,
    profile: RuntimeProfile,
) -> PipelineBundle:
    import aiohttp

    from pipecat.services.piper.tts import PiperHttpTTSService
    from pipecat.transcriptions.language import Language

    stt = _create_local_whisper_stt(settings=settings, profile=profile)
    llm = _create_openai_compatible_llm(
        settings=settings, profile=profile, name="ConfigurableHybridLLM"
    )

    http_session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=settings.piper_request_timeout_seconds)
    )
    if settings.tts_two_tier_enabled:
        from app.pipecat_runtime.two_tier_tts import TwoTierTTSService, piper_synthesize
        from app.pipecat_runtime.text_sanitizer import strip_emotion_tags
        from app.pipecat_runtime.vieneu_engine import VieNeuEngine

        logger.info(
            "two_tier_tts_enabled",
            opener="piper",
            expressive="vieneu_v3_turbo",
            opener_first=settings.tts_opener_first,
            vieneu_voice=settings.vieneu_voice or "(default)",
            vieneu_style=settings.vieneu_style,
            vieneu_speed=settings.vieneu_speed,
            vieneu_temperature=settings.vieneu_temperature,
        )

        voice = profile.tts.voice or settings.piper_voice
        vieneu = VieNeuEngine(
            voice=settings.vieneu_voice,
            speed=settings.vieneu_speed,
            temperature=settings.vieneu_temperature,
        )
        # Load the model NOW, not on the first expressive sentence — lazy load
        # would blow the render budget and silently fall back to Piper.
        vieneu.start_warm_up()

        async def _opener(text: str) -> tuple[bytes, int]:
            # Piper reads "[cười]" literally — strip emotion tags on this path.
            return await piper_synthesize(
                http_session, settings.piper_base_url, voice, strip_emotion_tags(text)
            )

        async def _expressive(text: str) -> tuple[bytes, int]:
            return await vieneu.synthesize(text, style=settings.vieneu_style)

        def _expressive_stream(text: str):
            return vieneu.synthesize_stream(text, style=settings.vieneu_style)

        tts = TwoTierTTSService(
            opener=_opener,
            expressive=_expressive,
            expressive_stream=_expressive_stream if settings.vieneu_streaming else None,
            opener_first=settings.tts_opener_first,
            first_sentence_timeout_s=settings.tts_expressive_first_sentence_timeout_seconds,
            text_filters=[VietnameseSpeechTextFilter()],
            name="TwoTierVietnameseTTS",
        )
        return _assemble_hybrid_bundle(
            transport, settings=settings, stt=stt, llm=llm, tts=tts,
            http_session=http_session,
        )
    try:
        tts = PiperHttpTTSService(
            base_url=settings.piper_base_url,
            aiohttp_session=http_session,
            text_aggregation_mode=TextAggregationMode.SENTENCE,
            text_filters=[VietnameseSpeechTextFilter(strip_tags=True)],
            settings=PiperHttpTTSService.Settings(
                voice=profile.tts.voice or settings.piper_voice,
                language=Language.VI_VN,
            ),
            name="LocalVietnamesePiperHTTP",
        )
    except Exception:
        await http_session.close()
        raise

    return _assemble_hybrid_bundle(
        transport, settings=settings, stt=stt, llm=llm, tts=tts,
        http_session=http_session,
    )


def _assemble_hybrid_bundle(
    transport: BaseTransport,
    *,
    settings: Settings,
    stt,
    llm,
    tts,
    http_session,
) -> PipelineBundle:
    context = LLMContext()
    user_aggregator, assistant_aggregator = _build_aggregators(context, settings)
    stt_guard = _build_stt_guard(settings)
    wake_gate = _build_wake_gate(settings, on_idle=None)
    manager, compactor = _build_context_guard(context, settings)
    grounding = TurnGroundingProcessor(context, name="TurnGrounding")
    small_talk = SmallTalkBypassProcessor(
        context, persona_name=settings.persona_name, name="SmallTalkBypass"
    )
    dedup = StreamDeduplicator(name="StreamDedup")
    resp_policy = ResponsePolicyProcessor(
        max_sentences=settings.response_max_sentences,
        max_words=settings.response_max_words,
        name="ResponsePolicy",
    )

    return PipelineBundle(
        pipeline=Pipeline(
            [
                transport.input(),
                stt,
                stt_guard,
                wake_gate,
                user_aggregator,
                compactor,
                grounding,
                small_talk,
                llm,
                dedup,
                resp_policy,
                tts,
                transport.output(),
                assistant_aggregator,
            ]
        ),
        context=context,
        stt=stt,
        llm=llm,
        tts=tts,
        context_manager=manager,
        wake_gate=wake_gate,
        resources=[http_session],
    )


async def create_pipeline(
    profile: RuntimeProfile,
    transport: BaseTransport,
    *,
    settings: Settings,
) -> PipelineBundle:
    if profile.name == "mock":
        bundle = _create_mock_pipeline(transport, settings=settings)
    elif profile.name == "google_vi":
        bundle = _create_google_vi_pipeline(transport, settings=settings, profile=profile)
    elif profile.name == "hybrid_local_vi":
        bundle = await _create_hybrid_local_vi_pipeline(
            transport, settings=settings, profile=profile
        )
    else:
        raise ValueError(f"Unsupported profile: {profile.name}")

    if bundle.wake_gate is not None:
        # Spec 8.7: returning to idle clears the transient visitor context.
        bundle.wake_gate.set_on_idle(bundle.reset_conversation)
    return bundle
