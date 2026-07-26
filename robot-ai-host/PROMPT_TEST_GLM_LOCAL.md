# PROMPT THỰC THI VÀ NGHIỆM THU LOCAL
## Robot AI Host Hybrid với GLM endpoint tại cổng 20128

Bạn là **Senior Pipecat Engineer, Realtime Voice QA Engineer, Python/FastAPI Engineer, WebRTC Engineer và DevOps Engineer**.

Hãy kiểm thử và sửa trực tiếp repository đang mở. Không tạo project mới. Không chỉ đọc code hoặc đưa hướng dẫn. Phải chạy lệnh thật, đọc log, sửa lỗi, bổ sung regression test và chạy lại toàn bộ bài kiểm thử.

Kiến trúc cần nghiệm thu:

```text
Microphone máy tính
→ Pipecat SmallWebRTCTransport
→ Silero VAD / turn management
→ Whisper STT local
→ OpenAI-compatible LLM gateway
→ model opencode-go/glm-5.1
→ sentence-level Piper TTS local
→ loa máy tính
```

Cấu hình LLM đã được preset:

```text
LLM_BASE_URL=http://127.0.0.1:20128/v1
LLM_MODEL=opencode-go/glm-5.1
```

API token là bí mật. Không yêu cầu người dùng gửi token vào chat, không in token, không ghi token vào source, prompt, log hoặc browser bundle. Token phải được nhập ẩn bằng:

```bash
.venv-hybrid/bin/python scripts/configure_glm_local.py
```

---

# 1. NGUYÊN TẮC BẮT BUỘC

1. Làm việc trong root repository hiện tại.
2. Không đổi Pipecat khỏi `pipecat-ai==1.6.0`.
3. Không đổi profile nghiệm thu khỏi `hybrid_local_vi`.
4. Không dùng Google STT/TTS trong bài nghiệm thu này.
5. Không dùng mock để tuyên bố voice pipeline đã đạt.
6. STT và TTS phải chạy local.
7. Chỉ transcript được gửi tới LLM endpoint; audio microphone không được gửi tới LLM.
8. Không hard-code API key.
9. Không báo PASS nếu chưa chạy.
10. Mỗi gate dùng đúng một trạng thái:

```text
PASS
FAIL
NOT RUN
BLOCKED
```

11. Nếu gặp lỗi, phải xác định root cause, sửa tối thiểu, thêm regression test và chạy lại.
12. Không làm mất các thay đổi chưa commit của người dùng.
13. Không kết luận hoàn thành nếu mic thật, loa thật và barge-in thật chưa PASS.

---

# 2. PHÁT HIỆN MÔI TRƯỜNG

Chạy và lưu vào `artifacts/glm-local-test/environment.txt`:

```bash
pwd
uname -a
uname -m
sw_vers 2>/dev/null || true
python3 --version
uv --version
node --version
npm --version
docker --version 2>/dev/null || true
lsof -nP -iTCP:20128 -sTCP:LISTEN 2>/dev/null || \
  ss -ltnp 2>/dev/null | grep ':20128' || true
```

Phân loại:

- macOS Apple Silicon: `LOCAL_STT_BACKEND=mlx`.
- Linux/NVIDIA: Faster-Whisper `cuda/float16`.
- CPU-only: Faster-Whisper `cpu/int8`, chọn model vừa tài nguyên.

Không dùng model quá lớn nếu máy thiếu RAM.

---

# 3. KIỂM TRA SOURCE VÀ SECRET

Xác minh tồn tại:

```text
.env.glm-local.example
GLM_LOCAL_ENDPOINT.md
scripts/configure_glm_local.py
scripts/check_llm_endpoint.py
scripts/run_glm_local_hybrid.sh
scripts/test_glm_local_project.sh
```

Chạy:

```bash
grep -R "PipelineTask\|PipelineRunner" -n app tests || true
grep -R "new RTCPeerConnection\|type.includes" -n clients/browser/src || true
grep -R "sk-" -n . \
  --exclude='.env' \
  --exclude-dir='.git' \
  --exclude-dir='node_modules' || true
git status --short || true
```

Yêu cầu:

- không có Pipecat API cũ;
- browser dùng Pipecat Client SDK;
- token không xuất hiện ngoài `.env`;
- `.env` được `.gitignore` loại trừ.

Nếu token từng bị chia sẻ công khai, khuyến nghị thu hồi và tạo token mới. Không tự động ghi lại token cũ.

---

# 4. CÀI ĐẶT HYBRID

Dùng Python 3.12:

```bash
uv python install 3.12
```

Trên macOS Apple Silicon:

```bash
chmod +x scripts/install_hybrid_macos.sh
./scripts/install_hybrid_macos.sh
```

Trên Linux:

```bash
chmod +x scripts/install_hybrid_linux.sh
./scripts/install_hybrid_linux.sh
```

Xác minh:

```bash
.venv-hybrid/bin/python --version
.venv-hybrid/bin/python -c \
  "import importlib.metadata as m; print(m.version('pipecat-ai'))"
```

Phải trả `1.6.0`.

---

# 5. TẠO `.env` AN TOÀN

Nếu `.env` chưa tồn tại:

```bash
cp .env.glm-local.example .env
```

Sau đó chạy:

```bash
.venv-hybrid/bin/python scripts/configure_glm_local.py
```

Script phải:

- hỏi token bằng input ẩn;
- ghi `.env` với quyền `0600` khi hệ điều hành hỗ trợ;
- đặt endpoint `http://127.0.0.1:20128/v1`;
- đặt model `opencode-go/glm-5.1`;
- không in token.

Kiểm tra không lộ secret:

```bash
stat -f '%Sp %N' .env 2>/dev/null || stat -c '%A %n' .env
```

Không dùng `cat .env` trong báo cáo.

---

# 6. TEST LLM GATEWAY TRƯỚC VOICE PIPELINE

Xác minh cổng:

```bash
lsof -nP -iTCP:20128 -sTCP:LISTEN 2>/dev/null || \
  ss -ltnp 2>/dev/null | grep ':20128'
```

Chạy probe chuẩn của repository:

```bash
.venv-hybrid/bin/python scripts/check_llm_endpoint.py
```

Probe phải kiểm tra:

1. `GET http://127.0.0.1:20128/v1/models` nếu endpoint hỗ trợ;
2. non-streaming `POST /v1/chat/completions`;
3. streaming SSE `POST /v1/chat/completions`;
4. model chính xác `opencode-go/glm-5.1`;
5. Bearer authentication;
6. token không xuất hiện trong output.

Kết quả streaming hợp lệ phải có các dòng `data: {...}` và có dữ liệu JSON. `[DONE]` được ưu tiên nhưng không bắt buộc nếu gateway đóng stream đúng chuẩn sau event cuối và Pipecat xử lý được.

Nếu `/models` trả 404 nhưng Chat Completions chạy, ghi WARN chứ không kết luận endpoint hỏng.

Nếu non-stream chạy nhưng stream fail:

- lưu response đã loại secret;
- xác định gateway không hoàn toàn tương thích OpenAI streaming;
- sửa adapter hoặc cấu hình nhỏ nhất;
- không tắt streaming âm thầm vì voice latency phụ thuộc streaming.

Lưu output:

```bash
.venv-hybrid/bin/python scripts/check_llm_endpoint.py \
  | tee artifacts/glm-local-test/llm-endpoint.txt
```

---

# 7. CÀI VÀ CHẠY PIPER LOCAL

Chạy:

```bash
chmod +x scripts/run_piper.sh
./scripts/run_piper.sh
```

Giữ terminal Piper đang chạy.

Terminal khác:

```bash
curl -i --max-time 5 http://127.0.0.1:5000/
```

HTTP 200, 400 hoặc 405 có thể chứng minh service reachable tùy API; HTTP 5xx hoặc connection refused là FAIL.

Thực hiện smoke TTS với câu:

```text
Xin chào, đây là thử nghiệm giọng nói tiếng Việt.
```

Lưu audio thành:

```text
artifacts/glm-local-test/piper-smoke.wav
```

Xác minh:

- file lớn hơn 1 KB;
- định dạng audio hợp lệ;
- phát được qua loa;
- người dùng nghe được tiếng Việt, không phải tone test.

macOS:

```bash
afplay artifacts/glm-local-test/piper-smoke.wav
```

Linux:

```bash
aplay artifacts/glm-local-test/piper-smoke.wav
```

Chất lượng giọng chỉ PASS sau khi người dùng nghe và xác nhận.

---

# 8. KIỂM TRA WHISPER LOCAL

Chạy profile check:

```bash
.venv-hybrid/bin/python scripts/check_hybrid_profile.py \
  --profile hybrid_local_vi \
  --load-stt
```

Nếu model cần tải, cho phép tải và lưu cache trên máy; không tải lại mỗi lần chạy.

Tạo hoặc dùng audio tiếng Việt có transcript biết trước:

```text
Tên tôi là Minh Hiếu.
```

Lưu kết quả:

```text
artifacts/glm-local-test/whisper-transcript.json
```

Gồm:

```json
{
  "expected": "Tên tôi là Minh Hiếu.",
  "actual": "...",
  "backend": "mlx hoặc faster-whisper",
  "model": "...",
  "audio_duration_ms": 0,
  "inference_ms": 0
}
```

Yêu cầu:

- transcript có nghĩa đúng;
- không hallucination rõ;
- ghi limitation nếu tên riêng sai;
- audio không rời khỏi máy qua STT cloud.

---

# 9. TEST PYTHON VÀ FRONTEND

Chạy script tổng hợp:

```bash
./scripts/test_glm_local_project.sh
```

Hoặc chạy riêng:

```bash
.venv-hybrid/bin/python -m pytest -q
npm ci --prefix clients/browser
npm run test --prefix clients/browser
npm run build --prefix clients/browser
```

Yêu cầu:

- không tính skip là PASS;
- ghi rõ test nào bị skip;
- `clients/browser/dist/` tồn tại;
- browser bundle không chứa token;
- endpoint/model chỉ được chuyển từ server config, không expose API key.

---

# 10. CHẠY HOST

Terminal 1 giữ Piper.

Terminal 2 chạy:

```bash
./scripts/run_glm_local_hybrid.sh \
  2>&1 | tee artifacts/glm-local-test/host.log
```

Script phải tự kiểm tra LLM endpoint và Hybrid profile trước khi mở host.

Kiểm tra:

```bash
curl -fsS http://127.0.0.1:8000/health
```

Mở Chrome/Chromium:

```text
http://127.0.0.1:8000/client
```

---

# 11. NGHIỆM THU MIC–LOA THẬT

## Test A — Kết nối

- chọn đúng microphone;
- cho phép quyền mic;
- connect;
- RTVI bot ready;
- transport connected;
- không có lỗi console.

## Test B — STT và phản hồi

Nói:

```text
Tên tôi là Minh Hiếu.
```

Yêu cầu:

- transcript hiển thị đúng ý;
- transcript được gửi tới model `opencode-go/glm-5.1`;
- phản hồi liên quan;
- Piper phát tiếng Việt thật qua loa.

## Test C — Context

Hỏi:

```text
Tôi vừa nói tên gì?
```

Bot phải trả đúng theo transcript trước đó.

## Test D — Sentence streaming

Nói:

```text
Hãy giới thiệu ngắn về bạn, sau đó nói bạn có thể giúp gì.
```

Yêu cầu:

- LLM trả ít nhất hai câu;
- câu đầu bắt đầu phát trước khi toàn bộ response hoàn tất;
- TTS nhận câu hoàn chỉnh, không nhận từng token;
- metrics có first sentence và TTS first audio.

## Test E — Barge-in thật

Khi bot đang nói, nói:

```text
Dừng lại.
```

Yêu cầu:

- audio cũ dừng;
- server hủy output cũ;
- stale audio không phát lại;
- lượt mới được xử lý;
- context không coi phần chưa phát là đã nói xong.

Không dùng nút dừng local playback để thay cho test này.

## Test F — Mute và reconnect

- mute: nói không tạo turn;
- unmute: STT hoạt động lại;
- disconnect/reconnect: session cũ cleanup, audio cũ không phát lại.

---

# 12. METRICS

Trước phiên test:

```bash
rm -f artifacts/runtime-metrics.jsonl
```

Thực hiện ít nhất 10 turn, sau đó:

```bash
.venv-hybrid/bin/python scripts/report_latency.py \
  artifacts/runtime-metrics.jsonl \
  | tee artifacts/glm-local-test/latency-report.txt
```

Báo cáo phải có `count`, `p50`, `p90`, `p95`, `max` cho các metric khả dụng.

Mục tiêu baseline:

| Metric | Gate |
|---|---:|
| Speech end → Whisper final P50 | ≤ 700 ms |
| LLM first event P50 | ≤ 700 ms |
| First token → first sentence P50 | ≤ 600 ms |
| Piper first audio P50 | ≤ 300 ms |
| User stop → audible start P50 | ≤ 1.9 s |
| Barge-in → audible stop P95 | ≤ 250 ms |

Nếu không đạt, xác định bottleneck cụ thể: VAD, Whisper, endpoint GLM, sentence aggregation, Piper hoặc playback.

---

# 13. TEST 4 THIẾT BỊ

Trước hết test control plane 4 session.

Không đặt `LOCAL_STT_MAX_SESSIONS=4` ngay.

1. Test một inference session.
2. Tăng lên hai session và theo dõi RAM/CPU.
3. Chỉ thử bốn session nếu hai session ổn định.

Dùng bốn identity:

```text
device-1: An
device-2: Bình
device-3: Chi
device-4: Dũng
```

Xác minh:

- không lẫn transcript;
- không lẫn context;
- không lẫn behavior;
- không lẫn metrics;
- cleanup đầy đủ.

Nếu nhiều model Whisper làm cạn RAM, ghi capacity limitation và đề xuất shared model pool/local inference service. Không che giấu giới hạn.

---

# 14. SOAK TEST

Chạy tối thiểu:

```text
30 phút
≥30 lượt
≥10 barge-in
≥5 reconnect
≥3 timeout LLM giả lập
```

Theo dõi:

- memory growth;
- CPU;
- file descriptors;
- orphan process;
- queue growth;
- stale audio;
- cleanup sau disconnect.

Lưu:

```text
artifacts/glm-local-test/soak.log
```

---

# 15. DOCKER

Native host là baseline ưu tiên trên Mac Apple Silicon.

Nếu chạy host trong Docker, `127.0.0.1:20128` không trỏ tới host machine. Đổi duy nhất trong `.env`:

```env
LLM_BASE_URL=http://host.docker.internal:20128/v1
```

Sau đó:

```bash
docker compose -f docker-compose.hybrid.yml build --no-cache
docker compose -f docker-compose.hybrid.yml up
```

Không copy `.env` hoặc API token vào image.

---

# 16. REVIEW 5 VÒNG

## Vòng 1 — Endpoint/API compatibility

Kiểm tra auth Bearer, model ID, `/models`, Chat Completions, SSE, timeout và error body.

## Vòng 2 — Pipecat/audio correctness

Kiểm tra Worker lifecycle, SmallWebRTC, RTVI, VAD, Whisper segmentation, sentence TTS và interruption.

## Vòng 3 — Context/isolation

Kiểm tra stale audio/text, context sau barge-in, reconnect và nhiều session.

## Vòng 4 — Security/reproducibility

Kiểm tra secret scan, `.env`, clean install, frontend build và scripts.

## Vòng 5 — Latency/capacity/scope

Kiểm tra bottleneck GLM, Whisper model size, Piper TTFA, RAM và code dư.

Mỗi vòng ghi vào `CHANGELOG_REVIEW.md`:

```text
finding
severity
root cause
files changed
fix
test evidence
remaining limitation
```

---

# 17. OUTPUT BẮT BUỘC

Tạo/cập nhật:

```text
LOCAL_GLM_TEST_REPORT.md
LOCAL_MIC_ACCEPTANCE.md
LOCAL_LATENCY_REPORT.md
LOCAL_CAPACITY_REPORT.md
TEST_EVIDENCE.md
KNOWN_LIMITATIONS.md
CHANGELOG_REVIEW.md
```

Artifacts:

```text
artifacts/glm-local-test/
├── environment.txt
├── llm-endpoint.txt
├── hybrid-profile.txt
├── python-tests.txt
├── frontend-tests.txt
├── frontend-build.txt
├── piper-smoke.wav
├── whisper-transcript.json
├── host.log
├── browser-console.log
├── latency-report.txt
├── capacity-report.txt
└── soak.log
```

Báo cáo cuối bắt đầu bằng:

```text
FINAL LOCAL GLM TEST STATUS: PASS / PARTIAL / FAIL
```

Sau đó liệt kê:

1. Environment.
2. LLM endpoint/model.
3. Authentication và streaming compatibility.
4. Whisper local.
5. Piper local.
6. Python/frontend tests.
7. Mic → STT → GLM → TTS → loa.
8. Sentence streaming.
9. Barge-in.
10. Metrics.
11. Reconnect.
12. Multi-session/capacity.
13. Soak.
14. Security.
15. Docker.
16. Các lỗi đã sửa.
17. Gate chưa đạt.
18. Lệnh tái hiện chính xác.

Không được kết luận hoàn thành nếu microphone vật lý, endpoint GLM streaming, Piper tiếng Việt, speaker playback và server-side barge-in chưa PASS.
