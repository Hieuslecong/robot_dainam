# 00 — Current Architecture Audit

## Entry Points
- **Server**: `app/main.py` → `uvicorn.run()` with FastAPI
- **Worker**: `app/pipecat_runtime/worker_factory.py` → `PipelineWorker` + `WorkerRunner`
- **Pipeline**: `app/pipecat_runtime/pipeline_factory.py` → `create_pipeline()`
- **Client**: `clients/browser/src/main.ts` → Pipecat Client JS + SmallWebRTC

## Pipecat Pipeline (hybrid_local_vi)
```
transport.input()
  → WhisperSTTServiceMLX (local MLX Whisper)
  → LLMUserAggregator (Silero VAD context)
  → OpenAILLMService (streaming, openai_compatible)
  → PiperHttpTTSService (sentence aggregation)
  → transport.output()
  → LLMAssistantAggregator (context storage)
```

## Service Locations
| Component | File | Class |
|-----------|------|-------|
| STT | `pipeline_factory.py:182` | `WhisperSTTServiceMLX` |
| LLM | `pipeline_factory.py:66` | `OpenAILLMService` |
| TTS | `pipeline_factory.py:240` | `PiperHttpTTSService` |

## System Prompt Location
- **File**: `app/pipecat_runtime/pipeline_factory.py` lines 26-33
- **Variable**: `VIETNAMESE_SYSTEM_PROMPT`
- **Content**: "Bạn là trợ lý hội thoại thân thiện của robot. Trả lời bằng tiếng Việt..."
- **Injected via**: `OpenAILLMService.Settings(system_instruction=...)`

## Conversation History
- **Storage**: `pipecat.processors.aggregators.llm_context.LLMContext`
- **Max turns**: Unlimited (no cap configured)
- **Per-session**: Isolated per `PipelineBundle`

## GPU/Device Selection
- **STT**: `config.py:163` — resolves `mlx` vs `faster-whisper` based on platform
- **LLM**: Remote endpoint — no local GPU
- **TTS**: Piper HTTP sidecar — no local GPU
- **PyTorch**: NOT configured — no MPS detection anywhere
- **No DeviceManager**: Device selection scattered across config.py

## LLM Configuration
- **Base URL**: `.env` → `LLM_BASE_URL`
- **Model**: `.env` → `LLM_MODEL`
- **Fallback**: `openai_api_key` / `openai_model` (legacy)
- **Settings class**: `app/config.py` → `Settings` (pydantic-settings)
- **No /settings page**: Frontend only has profile dropdown
- **os.getenv usage**: None found (uses pydantic-settings .env)

## Text Processing
- **Sanitizer**: `text_sanitizer.py` — removes Markdown/URLs for TTS
- **TextFilter**: `text_filter.py` — wraps sanitizer as Pipecat BaseTextFilter
- **No response policy**: No length limit, no truncation, no dedup

## Duplicate Sentences — Root Cause Analysis
The pipeline flow:
1. LLM streams tokens → sentence aggregator splits into sentences
2. Each sentence → TTS service generates audio
3. Assistant response → context aggregator stores in LLMContext
4. Response text → transport.output() → client UI

**Potential duplicate paths:**
- The TTS service pushes `TTSAudioRawFrame` AND the text reaches the output via a separate path
- The assistant aggregator stores AND forwards the response
- Pipecat's `LLMContextAggregatorPair` handles both user AND assistant frames — the assistant aggregator may push text frames downstream in addition to the TTS service doing so
- WebRTC transport may re-emit on reconnect

**Most likely cause**: The `TextFrame` from LLM flows through BOTH the TTS service AND the assistant aggregator. Both push to output, causing duplicate display. The TTS service converts text to audio, but the original TextFrame still reaches the output transport.

## Persona "Antigravity" — Root Cause
- The `VIETNAMESE_SYSTEM_PROMPT` does NOT mention Antigravity
- The Gemini model (`agy/gemini-3.1-flash-lite`) self-identifies as Antigravity because that's the gateway provider name
- The system prompt is too weak: "Bạn là trợ lý hội thoại thân thiện của robot" — no explicit prohibition on self-identifying as a company
- The model generates its own identity when asked

## STT Noise — Root Cause
- No minimum speech duration check
- No echo suppression (TTS output → mic pickup)
- No duplicate transcript hash
- No assistant-speaking gate (STT runs while TTS is playing)
- Partial transcripts are passed through the aggregator
- Background audio from videos/speakers gets transcribed and sent to LLM
