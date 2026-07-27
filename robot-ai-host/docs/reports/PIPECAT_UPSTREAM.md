# Pipecat Upstream Reference

| Field | Value |
|---|---|
| Repository | https://github.com/pipecat-ai/pipecat |
| Tag | v1.6.0 |
| Commit | 08e871599904080cedad7ce5683676ab8481fa59 |
| Package | pipecat-ai==1.6.0 |
| Python extras | webrtc, google, silero |
| Client SDK | @pipecat-ai/client-js==1.12.0 |
| Client transport | @pipecat-ai/small-webrtc-transport==1.10.5 |

`vendor/pipecat-reference/UPSTREAM_COMMIT` cho phép xác minh ZIP không có `.git` metadata.

## Public APIs used

- `Pipeline`, `PipelineParams`, `PipelineWorker`
- `WorkerRunner`
- `SmallWebRTCRequestHandler`, POST/PATCH request models
- `SmallWebRTCTransport`, `TransportParams`
- `RTVIProcessor` auto-created by `PipelineWorker(enable_rtvi=True)`
- `LLMContext`, `LLMContextAggregatorPair`, `LLMUserAggregatorParams`
- `SileroVADAnalyzer`
- `GoogleSTTService`, `OpenAILLMService`, `GoogleTTSService`
- `TTSService`, `TextAggregationMode.SENTENCE`
- `UserBotLatencyObserver`, Pipecat metrics frames
- `BaseTextFilter`

## Source/examples inspected

- `src/pipecat/pipeline/worker.py`
- `src/pipecat/workers/runner.py`
- `src/pipecat/transports/smallwebrtc/request_handler.py`
- `src/pipecat/processors/frameworks/rtvi/processor.py`
- `src/pipecat/processors/aggregators/llm_response_universal.py`
- `src/pipecat/services/google/stt.py`
- `src/pipecat/services/google/tts.py`
- `src/pipecat/services/openai/llm.py`
- `src/pipecat/services/tts_service.py`
- `examples/multi-worker/ui-worker/shopping-list/client`
- official SmallWebRTC transport examples/tests in the locked tree

## Verification

```bash
uv run python scripts/verify_deps.py
python scripts/verify_upstream_source.py
```
