# Architecture

## 1. Thành phần

```text
Pipecat Client SDK (browser)
  │ REST bootstrap + JWT
  │ SmallWebRTC audio/data
  ▼
FastAPI
  ├─ device registration
  ├─ session ownership / heartbeat / max=4
  ├─ session-scoped WebRTC token
  └─ SmallWebRTCRequestHandler POST/PATCH
          ▼
SmallWebRTCTransport per session
          ▼
PipelineWorker per session
  input → STT → user aggregator → LLM → sentence TTS → output → assistant aggregator
```

## 2. Pipecat runtime

Mỗi session tạo riêng:

- transport;
- STT/LLM/TTS service;
- `LLMContext`;
- `LLMContextAggregatorPair`;
- `Pipeline`;
- `PipelineWorker`;
- `WorkerRunner`;
- metrics observers.

Không có global conversation context hoặc provider state dùng chung.

## 3. Turn management và barge-in

`SileroVADAnalyzer` được cấu hình trong `LLMUserAggregatorParams`. Khi user bắt đầu nói trong lúc bot đang nói, Pipecat phát interruption và downstream LLM/TTS phải dừng. Ứng dụng không tạo cancellation framework song song.

Hai phép đo riêng:

- server frame: `UserStartedSpeakingFrame → BotStoppedSpeakingFrame`;
- client: `onUserStartedSpeaking → onBotStoppedSpeaking`.

Nút “Dừng loa cục bộ (debug)” không được tính là barge-in.

## 4. RTVI

`PipelineWorker(enable_rtvi=True)` chịu trách nhiệm event chuẩn:

- bot ready;
- user/bot speaking;
- transcript;
- bot output;
- metrics;
- errors.

Custom messages chỉ dùng cho:

- `robot.behavior`;
- `robot.behavior.ack`;
- `client.playback.started`;
- `client.barge_in.stopped`;
- `client.webrtc.connected`;
- capability/mute/error metadata.

## 5. Sentence-level TTS

Cả mock TTS và Google TTS đều cấu hình `TextAggregationMode.SENTENCE`. Mock tone được tạo một lần cho mỗi câu aggregate và không đại diện cho giọng nói tự nhiên.

## 6. Session lifecycle

```text
CREATED → ACTIVE → CLOSING → CLOSED
                  ↘ ERROR
```

Close là idempotent. Runner được cancel khi session đóng; runner dùng auto-end mặc định để tránh task treo sau khi worker kết thúc.

## 7. Security boundary

LLM không được sinh servo ID, angle hoặc speed. Deterministic states lấy từ RTVI. Expressive behavior đi qua allowlist và validator trước khi gửi client.

## Hybrid local voice profile

`hybrid_local_vi` reuses the same FastAPI, WebRTC, RTVI, session, metrics and behavior layers. Only providers change:

```text
WhisperSTTServiceMLX or WhisperSTTService
→ OpenAILLMService(base_url/token/model from Settings)
→ PiperHttpTTSService(TextAggregationMode.SENTENCE)
```

Each Hybrid session owns its own LLM service, STT service and `aiohttp.ClientSession` for Piper. Session cleanup closes the Piper HTTP client. The default `LOCAL_STT_MAX_SESSIONS=1` prevents accidental loading of multiple large Whisper models before capacity testing.
