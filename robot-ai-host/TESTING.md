# Testing

## 1. Automated tests

```bash
uv sync --frozen
uv run pytest -q
npm ci --prefix clients/browser
npm run test --prefix clients/browser
npm run build --prefix clients/browser
```

Tests gồm:

- auth/session ownership/lifecycle;
- default profile và cloud fail-fast;
- session-scoped `webrtcUrl`;
- metrics JSONL/filter/percentiles;
- four-session metadata isolation;
- behavior validation và raw motor rejection;
- Vietnamese text sanitizer;
- runner cancellation cleanup;
- browser source contract: official SDK, không raw RTCPeerConnection, không heuristic protocol parsing.

## 2. Upstream verification

```bash
uv run python scripts/verify_deps.py
uv run python scripts/verify_upstream_source.py
```

`verify_deps.py` cần package Pipecat đã cài. `verify_upstream_source.py` kiểm tra AST trực tiếp trên source tag v1.6.0, nên chạy được cả khi sandbox không cài dependencies.

## 3. Mock mode

```bash
uv run python -m app.main --profile mock
```

Mock chỉ kiểm tra:

- Pipecat frame/control flow;
- VAD-triggered scripted transcript;
- token-streaming mock LLM;
- sentence aggregation;
- tone audio transport;
- RTVI/custom messages.

Không dùng mock để đánh giá WER, TTS tiếng Việt hoặc latency cloud.

## 4. Cloud mode

```bash
uv run python scripts/check_cloud_profile.py --profile google_vi
uv run python -m app.main --profile google_vi
```

Sau đó làm bài test trong `MANUAL_MIC_ACCEPTANCE.md`.

## 5. Control-plane load test

```bash
uv run python scripts/load_test.py \
  --server http://127.0.0.1:8000 \
  --clients 4 \
  --duration 900 \
  --profile mock
```

Script này chỉ kiểm tra register/session/heartbeat/ownership/cleanup. Trường `webrtc_media_tested` luôn là `false` để tránh claim sai.

## 6. Media concurrency test

Mở bốn browser context với bốn device ID và làm bài identity test:

- device-1: An
- device-2: Bình
- device-3: Chi
- device-4: Dũng

Mỗi tab phải nhớ đúng identity riêng. Đây là test media/context thật, không thể thay bằng REST load test.

## 7. Metrics

```bash
uv run python scripts/report_latency.py artifacts/runtime-metrics.jsonl
```

Chỉ so với gate latency sau khi có microphone, cloud providers và audio playback thật.
