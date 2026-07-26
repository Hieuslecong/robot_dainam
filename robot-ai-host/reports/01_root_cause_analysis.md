# 01 — Root Cause Analysis

## Issue 1: CPU-only on Mac (no Apple GPU)
**Root cause**: No PyTorch MPS detection exists anywhere in the codebase. `config.py` only handles STT backend selection. No `torch.backends.mps` check. No `DeviceManager`.

**Files affected**:
- `app/config.py` — missing `PYTORCH_DEVICE`, MPS detection
- `app/pipecat_runtime/pipeline_factory.py` — no device parameter for LLM/TTS

## Issue 2: No unified LLM config
**Root cause**: Settings are spread across `.env` and `config.py`. No UI to change endpoint/model at runtime. No `/settings` page exists.

**Files affected**:
- `.env` — fragile, requires restart
- `app/config.py` — good Settings class but no runtime update
- `clients/browser/` — no settings UI

## Issue 3: Long, repetitive responses
**Root cause**: 
- No `max_tokens` enforced in LLM request (defaults to model max)
- No response length policy post-LLM
- `VIETNAMESE_SYSTEM_PROMPT` says "Câu đầu tiên ngắn, tối đa 8 đến 12 từ; sau đó mới giải thích thêm" but LLM often ignores this
- Temperature not configured low enough (default ~1.0)

**Files affected**:
- `pipeline_factory.py:26` — system prompt too permissive
- `pipeline_factory.py:78` — no max_tokens in OpenAILLMService.Settings

## Issue 4: Wrong persona (Antigravity/DeepMind/programmer)
**Root cause**: 
- `agy/gemini-3.1-flash-lite` is served through a gateway named "Antigravity"
- The model has RLHF training that self-identifies as a coding assistant
- System prompt doesn't explicitly PROHIBIT self-identification as a company
- No assistant profile YAML exists

**Files affected**:
- `pipeline_factory.py:26-33` — system prompt too weak
- No `config/assistant_school.yaml` exists

## Issue 5: Each sentence displayed/played twice
**Root cause**: In Pipecat's LLMContextAggregatorPair, the assistant aggregator receives TextFrames from the LLM AND forwards them downstream. Simultaneously, the TTS service receives the same TextFrames and generates audio. Both paths push to transport.output(). This creates two copies of text reaching the client.

The pipeline order is:
```
LLM → TextFrames → TTS (sentence agg → audio)
                 → Assistant Aggregator (context storage → forward to output)
```

The assistant aggregator forwards `TextFrame` to output AFTER TTS already processed them. The client receives the text twice.

**Files affected**:
- `pipeline_factory.py:99-116` — pipeline processor chain
- Client: no deduplication on received text

## Issue 6: STT captures speaker/video audio
**Root cause**:
- No echo cancellation (AEC) configured
- No assistant-speaking gate — STT active while TTS plays
- No minimum speech duration filter
- No duplicate transcript hash
- `WHISPER_NO_SPEECH_PROB=0.6` may be too permissive
- VAD triggers for any audio above silence threshold

**Files affected**:
- `pipeline_factory.py:197-206` — Whisper config
- No `stt_guard.py` processor exists
- No echo suppression in transport

## Issue 7: Partial STT sent to LLM  
**Root cause**: The `LLMUserAggregator` receives all frames from STT including `InterimTranscriptionFrame`. When VAD detects end of speech, the aggregator triggers inference with whatever accumulated text it has — including partial/noisy transcripts.

**Files affected**:
- `pipeline_factory.py:59-63` — `_build_aggregators` uses default params
- No transcript filtering before aggregator
