# MASTER IMPLEMENTATION PROMPT
## Upgrade `robot-ai-host` into an Intelligent, Expressive, Multi-Task Vietnamese Realtime Agent

Bạn là:

- Principal Realtime Voice AI Engineer
- Senior Pipecat Engineer
- Vietnamese ASR Evaluation Engineer
- Agent Systems Architect
- Local TTS Engineer
- Security and Reliability Engineer
- QA Lead

Nhiệm vụ của bạn là nâng cấp **repository hiện tại đang mở trong workspace**. Không tạo project không liên quan. Không chỉ phân tích hoặc viết kế hoạch. Phải đọc code thật, triển khai, chạy test, sửa lỗi, đánh giá nhiều vòng và tạo bằng chứng nghiệm thu.

Tài liệu nguồn chuẩn:

```text
ROBOT_AI_AGENT_MASTER_SPECIFICATION_v1_1.md
```

Đọc toàn bộ tài liệu trên trước khi thay đổi code. **Spec là nguồn sự thật duy nhất cho nội dung nghiệp vụ** (persona, tool list, intent taxonomy, schema, gate): khi prompt này và spec khác nhau, spec thắng.

## CHẾ ĐỘ CHẠY — QUAN TRỌNG NHẤT

Prompt này KHÔNG được thực hiện như một phiên duy nhất chạy hết sáu phase. Quy tắc:

1. **Mỗi phiên làm trọn vẹn MỘT phase** (theo thứ tự Phase 0 → 6), kết thúc bằng: gate check + báo cáo phase + commit trên branch upgrade. Phiên sau bắt đầu bằng đọc báo cáo các phiên trước.
2. **Thứ tự ưu tiên khi hết thời gian/context/tài nguyên:**

```text
Phase 0 HOÀN CHỈNH > Phase 1 HOÀN CHỈNH > Phase 2 > ... > DỪNG
```

Một phase hoàn chỉnh có giá trị hơn ba phase dở dang. Tuyệt đối không trải mỏng "mỗi phase một ít" — đó là chế độ thất bại chính của loại nhiệm vụ này.
3. Nếu môi trường chỉ cho phép một phiên: làm Phase 0 đến hết gate, rồi dừng và ghi rõ trạng thái các phase còn lại là `NOT RUN`.

---

# 1. MỤC TIÊU

Chuyển hệ thống từ:

```text
Mic
→ SmallWebRTC
→ local STT
→ một LLM
→ Piper
→ speaker
```

thành:

```text
Mic
→ SmallWebRTC/RTVI
→ local Vietnamese STT profiles
→ intent/complexity/risk router
→ một Agent Orchestrator
→ Pipecat Flows + typed tools
→ knowledge hoặc external action
→ Response Composer
→ Expression Composer
→ VieNeu local TTS
→ Piper fallback
→ speaker + validated robot behavior
```

Kết quả phải:

- chính xác tiếng Việt hơn;
- nói tự nhiên hơn;
- có cảm xúc đúng ngữ cảnh;
- thực hiện được tác vụ thật;
- an toàn khi gọi tool;
- cấu hình qua biến môi trường;
- kiểm thử được trên Mac M1;
- sẵn sàng mở rộng sang server GPU và robot thật.

---

# 2. RÀNG BUỘC BẮT BUỘC

1. Giữ Pipecat `1.6.0` trừ khi chứng minh được incompatibility blocking bằng source và test.
2. Giữ FastAPI, SmallWebRTC, RTVI, session isolation và provider profiles.
3. Không chuyển sang voice framework khác.
4. Không xây multi-agent swarm.
5. Dùng một orchestrator + typed tools + Pipecat Flows.
6. Không hard-code LLM endpoint, token hoặc model.
7. Giữ:

```env
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
LLM_DEFAULT_HEADERS_JSON=
```

8. STT và TTS phải có local profile.
9. Piper phải còn làm fallback.
10. Không báo tool thành công trước ACK.
11. Không thực hiện write action nếu chưa xác nhận đúng policy.
12. Không cho LLM phát raw servo/motor commands.
13. Không lưu toàn bộ transcript làm long-term memory.
14. Không lộ secret trong source, log, test, frontend hoặc report.
15. Không báo `PASS` nếu chưa chạy test thật.
16. Không phá profile đang hoạt động.
17. Không tạo microservice không cần thiết.
18. Mỗi bug sửa phải có regression test.
19. Ghi limitation trung thực.
20. Khi repository thực tế khác đặc tả, ưu tiên code thật nhưng không được làm yếu mục tiêu thiết kế.
21. Không bịa model download, audio result, metric hoặc user evaluation.
22. Không xóa thay đổi chưa commit của người dùng.
23. Tuân thủ CHẾ ĐỘ CHẠY: một phiên một phase, ưu tiên hoàn chỉnh theo thứ tự, không trải mỏng.
24. Mọi việc cần con người thật (mic, nghe audio, panel A/B, thu corpus, reconnect vật lý) phải được gom vào `HUMAN_TASK_CHECKLIST.md` với hướng dẫn thực hiện cụ thể — không chỉ đánh dấu BLOCKED rải rác.
25. Router phải tuân mục 9.8 của spec: bypass heuristic trước, budget ≤300 ms, timeout không chặn turn.

---

# 3. AUDIT BAN ĐẦU

Chạy và lưu:

```bash
pwd
git status --short
find . -maxdepth 3 -type f | sort
python3 --version
node --version
npm --version
uname -a
uname -m
```

**Phát hiện tooling thật của repo — không giả định:**

```bash
# Repo hiện tại dùng .venv-hybrid + PYTHONPATH, có thể KHÔNG có uv/pyproject.toml
ls .venv-hybrid/bin/python .venv-piper/bin/python 2>/dev/null
ls pyproject.toml uv.lock requirements*.txt 2>/dev/null
command -v uv || echo "uv KHONG co - dung venv truc tiep"
```

Quy tắc: dùng đúng cách chạy test/lệnh mà repo đang dùng (ví dụ `.venv-hybrid/bin/python -m pytest`). Chỉ dùng `uv` nếu repo đã có `uv.lock`. Không tự ý migrate tooling trong Phase 0 — migrate tooling là thay đổi riêng, cần lý do và test.

Tìm:

```text
pyproject.toml
uv.lock
app/
clients/browser/
config/
configs/
tests/
scripts/
.env*.example
```

Xác định:

- file profile đang active;
- config bị trùng;
- STT builder;
- LLM builder;
- TTS builder;
- session lifecycle;
- context aggregator;
- VAD/Smart Turn;
- response processors;
- metrics observers;
- browser capture constraints;
- function calling hiện tại;
- memory hiện tại;
- license inventory.

Tạo:

```text
reports/upgrade/00_repository_audit.md
```

Backup:

```bash
git switch -c upgrade/intelligent-expressive-agent 2>/dev/null || true
mkdir -p artifacts/upgrade
git diff > artifacts/upgrade/pre-upgrade.patch 2>/dev/null || true
```

---

# 4. PHASE 0 — FOUNDATION CLEANUP

## 4.1 Config

Chọn một configuration directory chính.

Xử lý ambiguity `config/` và `configs/`.

Yêu cầu:

- một runtime source of truth;
- test chứng minh source active;
- path cũ bị loại hoặc chỉ là generated compatibility mirror;
- không silent fallback giữa hai file.

## 4.2 Dependency

Pin direct Python và frontend dependencies.

Ghi model identifier, revision và checksum nếu có.

Tạo:

```text
DEPENDENCY_LOCK_REPORT.md
MODEL_INVENTORY.md
LICENSE_INVENTORY.md
```

Không khẳng định license khi chưa xác minh.

## 4.3 Persona

Thay persona lặp/xung đột bằng persona định nghĩa tại **spec mục 9.4–9.5** (nguồn duy nhất — không chép lại vào đây để tránh hai nguồn sự thật lệch nhau).

Yêu cầu triển khai:

- Tên persona đọc từ config (`PERSONA_NAME`), không hard-code — tên "N.E.K.O" chưa được nhà trường xác nhận (xem cảnh báo trong spec 9.4).
- Loại bỏ câu boilerplate "sẵn sàng hỗ trợ" và câu lặp vai trò trong prompt cũ.
- Rút ngắn core prompt về ngân sách spec 9.7 (500–800 token core).
- Chuyển hard length policy sang processor khi phù hợp.

## 4.4 Context

Thực hiện:

- recent-turn limit;
- context summarization;
- task-state preservation;
- reset conversation;
- disconnect cleanup.

Không cắt tool-call sequence chưa hoàn tất.

## 4.5 Metrics

Đồng bộ timeline:

```text
physical_speech_start
vad_speech_start
physical_speech_end
vad_speech_end
turn_finalized
stt_final
llm_request_start
llm_first_token
first_speakable_chunk
tts_request_start
tts_first_audio
server_audio_sent
client_audio_received
client_audible_start
interruption_detected
client_audio_stopped
```

Report:

```text
count
p50
p90
p95
max
```

Không đánh dấu đạt nếu vượt target.

## 4.6 Browser capture

Xác minh và expose:

```text
echoCancellation
noiseSuppression
autoGainControl
```

Không xây duplicate AEC trước khi test browser AEC.

## 4.7 Test Phase 0

Dùng runner đã phát hiện ở mục 3 (ví dụ với repo hiện tại):

```bash
.venv-hybrid/bin/python -m pytest tests/ -q
npm ci --prefix clients/browser
npm run test --prefix clients/browser
npm run build --prefix clients/browser
```

(Chỉ thay bằng `uv run pytest -q` nếu repo đã có uv.lock.)

Tạo:

```text
reports/upgrade/01_foundation_cleanup.md
```

---

# 5. PHASE 1 — STT TIẾNG VIỆT

## 5.1 Profile

Tạo (theo spec mục 8.1):

```text
stt_fast_vi
stt_balanced_vi
stt_accurate_vi
stt_research_vi
stt_streaming_vi
```

Mapping ứng viên:

```text
stt_fast_vi:
Whisper large-v3-turbo q4 hiện tại

stt_balanced_vi:
Whisper large-v3-turbo 8-bit MLX
(LƯU Ý: 8-bit nặng hơn q4 → speech-end→final sẽ CHẬM HƠN hiện trạng;
đo và ghi trung thực, không mặc định nó qua gate ≤900ms)

stt_accurate_vi:
PhoWhisper-medium hoặc runtime conversion đã xác minh

stt_research_vi:
Whisper large-v3 8-bit MLX

stt_streaming_vi:
VietASR/Zipformer qua sherpa-onnx (streaming)
— ứng viên duy nhất giải quyết gate latency tận gốc nếu batch Whisper trượt
```

Model không có sẵn không được làm toàn app import fail. Failure phải isolate theo selected profile.

## 5.2 Benchmark corpus

Hỗ trợ manifest tối thiểu 200 utterance:

```text
benchmarks/stt/manifest.jsonl
benchmarks/stt/audio/
benchmarks/stt/glossary.yaml
```

Category:

- Bắc/Trung/Nam;
- nam/nữ;
- nhanh/chậm;
- câu ngắn/dài;
- tên;
- khoa/phòng;
- mã sinh viên;
- ngày;
- phòng;
- thuật ngữ trường;
- Việt–Anh;
- noise;
- echo;
- silence.

**Vòng 1 — chạy được ngay, không chờ thu âm:** tải và benchmark trên corpus công khai có ground truth (VIVOS, Common Voice-vi, VLSP test set) theo spec 23.1. Vòng 1 dùng để xếp hạng sơ bộ và loại ứng viên yếu.

**Vòng 2 — corpus tự thu:** nếu chưa có audio thật, tạo schema + manifest, thêm việc thu âm vào HUMAN_TASK_CHECKLIST.md và đánh dấu runtime benchmark vòng 2 `BLOCKED`; không tạo số giả. Không chốt STT mặc định chỉ bằng vòng 1.

## 5.3 Metric

Đo:

```text
WER
CER
semantic accuracy
proper-name accuracy
number/date accuracy
silent hallucination
speech-end → final
RAM
CPU/GPU
```

## 5.4 Glossary correction

- versioned glossary;
- confidence threshold;
- giữ original transcript;
- log correction;
- không đoán khi confidence thấp.

## 5.5 Critical field

Các trường không chắc chắn phải xác nhận trước write tool.

## 5.6 VAD

Test:

- start/stop threshold;
- min speech;
- stop padding;
- min volume;
- short utterance;
- final syllable;
- barge-in.

## 5.7 Gate

Không tự chọn model nào theo cảm giác — benchmark quyết định.

Ứng viên ban đầu ưu tiên về accuracy:

```text
Whisper large-v3-turbo 8-bit
```

Nhưng lưu ý spec 8.1/8.6: 8-bit gần như chắc chắn trượt gate latency ≤900 ms trên M1 (nặng hơn q4 vốn đã mất ~1.9 s). Nếu benchmark xác nhận mọi profile batch trượt latency, `stt_streaming_vi` (VietASR/Zipformer) trở thành ứng viên mặc định bắt buộc benchmark. Ghi trung thực trade-off accuracy/latency của từng profile trong report — không giấu profile trượt.

Tạo:

```text
reports/upgrade/02_stt_benchmark.md
artifacts/upgrade/stt-results.json
```

---

# 6. PHASE 2 — LOCAL EXPRESSIVE TTS

## 6.1 Profile

Tạo (theo spec mục 16.1):

```text
expressive_local_vi
lightweight_local_vi
fallback_local_vi
cloud_expressive_vi   # tùy chọn — Plan B nếu VieNeu trượt gate
```

Mapping:

```text
expressive_local_vi:
VieNeu expressive local model

lightweight_local_vi:
VieNeu 0.3B quantized

fallback_local_vi:
Piper HTTP vi_VN-vais1000-medium
(đồng thời là TẦNG MỞ MÀN trong kiến trúc hai tầng — spec 16.2a)

cloud_expressive_vi:
Qwen-Audio-3.0-TTS, endpoint Singapore, opt-in qua .env
```

Không xóa Piper hiện tại.

**Bắt buộc triển khai kiến trúc hai tầng theo spec 16.2a** — Piper phát câu/ack đầu (TTFA ≤500 ms), VieNeu render câu tiếp theo trong khi câu đầu phát. Đây là cơ chế chính để đạt gate TTFA, không phải tối ưu phụ. Gate TTFA áp cho audio đầu tiên nghe được của turn, không áp cho engine biểu cảm đứng riêng.

## 6.2 Sidecar abstraction

TTS adapter hỗ trợ:

- health;
- warmup;
- synthesize;
- cancel;
- timeout;
- fallback;
- metrics;
- style mapping.

Nếu Pipecat chưa có VieNeu integration trực tiếp, tạo local sidecar adapter. Không nhúng model internals sâu vào pipeline.

## 6.3 Expression Composer

Typed schema:

```json
{
  "spoken_text": "string",
  "style": "neutral|friendly|cheerful|calm|empathetic|encouraging|serious",
  "intensity": 0.0,
  "speaking_rate": 1.0,
  "pause_profile": "normal",
  "robot_behavior": "attentive_idle",
  "screen_payload": null
}
```

Yêu cầu:

- metadata không vào spoken text;
- style allowlist;
- intensity bounded;
- default friendly;
- serious/empathetic phải có lý do ngữ cảnh;
- unknown style fallback.

## 6.4 Prosody-aware chunking

- không token-level;
- không fragment 2–4 từ;
- chunk đầu đủ nghĩa;
- ghép câu ngắn liên quan;
- một voice/style mỗi turn;
- cancel queued audio khi barge-in;
- không stale audio sau reconnect.

## 6.5 Voice identity

Hỗ trợ reference voice có consent.

Ghi:

- quyền sử dụng;
- recording condition;
- styles;
- language coverage;
- checksum;
- storage policy.

Không clone giọng khi chưa có quyền.

## 6.6 TTS benchmark

Tối thiểu 80 câu.

Đo:

```text
naturalness
emotion correctness
proper-name pronunciation
Vietnamese-English pronunciation
audio corruption
TTFA
RTF
memory
barge-in
voice consistency
```

Blind A/B:

```text
Piper
VieNeu light
VieNeu expressive
```

Tạo:

```text
reports/upgrade/03_tts_benchmark.md
artifacts/upgrade/tts-results.json
```

## 6.7 Gate

Theo spec 16.6 (đã sửa v1.1):

```text
naturalness ≥4.2/5                    # cần panel người nghe — spec 23.2a
preference over Piper ≥80%            # cần panel — chưa có panel = BLOCKED
emotion correctness ≥85%              # cần panel
proper-name pronunciation ≥95%
TTFA P50 ≤500 ms                      # audio đầu tiên của turn (tầng mở màn)
khoảng lặng giữa hai tầng P95 ≤700 ms
barge-in stop P95 ≤250 ms
```

Thang leo khi trượt gate, theo thứ tự: (1) light profile làm tầng biểu cảm; (2) kích hoạt `cloud_expressive_vi`; (3) chỉ khi cả ba đường đều trượt mới kết luận Phase thất bại. Các gate cần panel người nghe: ghi `BLOCKED` + thêm vào HUMAN_TASK_CHECKLIST.md, không tự chấm.

---

# 7. PHASE 3 — ADAPTIVE LLM ROUTING

## 7.1 Env

Giữ:

```env
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
LLM_DEFAULT_HEADERS_JSON=
```

Bổ sung optional:

```env
LLM_ROUTER_MODEL=
LLM_EXECUTOR_MODEL=
LLM_PLANNER_MODEL=
```

## 7.2 Capability probe

Test từng model:

```text
/models
non-stream
stream SSE
structured output
function calling
tool_choice
reasoning_content
cancellation
timeout
empty content
```

Không log API key.

## 7.3 Router schema

```json
{
  "intent": "small_talk",
  "complexity": "simple",
  "risk": "read_only",
  "confidence": 0.95,
  "requires_tool": false,
  "requires_flow": false
}
```

## 7.4 Routing

**Tuân spec mục 9.8 — ràng buộc cứng:**

- Heuristic bypass (rule/regex/keyword local, không LLM) cho greeting, small talk phổ biến, lệnh dừng — mục tiêu bypass ≥60% lượt.
- Khi gọi LLM router: model nhỏ nhất đạt structured output, P50 ≤300 ms, non-streaming, max_tokens tối thiểu.
- Router timeout ⇒ đi thẳng conversation executor với intent `unclear`, không chặn turn.
- Metrics: expose `router_latency` và `router_bypass_rate`.

Fast model:

- extraction;
- read-only lookup;
- simple tool.

Planner:

- multi-step;
- high-impact ambiguity;
- multiple tools;
- retry/recovery;
- complex synthesis.

Không gọi mọi model cho mọi turn.

## 7.5 Response Composer

- result first;
- natural Vietnamese;
- không boilerplate;
- độ dài theo intent;
- một câu hỏi rõ khi thiếu dữ liệu;
- success/partial/failure trung thực;
- detail dài sang screen payload.

Tạo:

```text
reports/upgrade/04_llm_routing_and_persona.md
```

---

# 8. PHASE 4 — AGENT ORCHESTRATOR VÀ TOOLS

## 8.1 Một orchestrator

Dùng Pipecat function calling và Pipecat Flows.

Không tạo specialist agent nếu chưa có gate.

## 8.2 Intent

```text
small_talk
school_information
knowledge_lookup
personal_productivity
action_request
sensitive_action
robot_behavior_request
unclear
unsupported
```

## 8.3 Tool

Danh sách và phân loại theo **spec mục 11.1** (nguồn duy nhất). Tóm tắt scope:

```text
Read-only + personal:      triển khai đầy đủ, backend thật
Action MVP:                create_reminder (backend local thật),
                           draft_email (soạn, không gửi)
Action interface-only:     create_calendar_event, send_email,
                           create_support_ticket
                           → adapter + fake test, KHÔNG tính vào acceptance
Robot:                     set_robot_behavior, show_screen_content
```

Fake adapter chứng minh contract, không chứng minh an toàn — không dùng fake làm bằng chứng production hay bằng chứng gate "zero false success".

## 8.4 Tool envelope

```json
{
  "tool_call_id": "string",
  "tool_name": "string",
  "status": "success|partial|failed|timeout|denied",
  "data": {},
  "message": "string",
  "error_code": null,
  "retryable": false,
  "timestamp": "ISO-8601"
}
```

## 8.5 Confirmation

Bắt buộc trước:

```text
send_email
create/change calendar event
create_support_ticket
submit_form
delete
protected device action
```

Confirmation phải đọc lại normalized critical fields.

## 8.6 Task state

```text
task_id
intent
risk_level
current_node
collected_fields
missing_fields
normalized_fields
confirmation_status
tool_calls
tool_results
retry_count
status
```

## 8.7 Truthful completion

Chỉ nói hoàn tất khi tool envelope `success`.

Timeout/partial phải nói đúng trạng thái.

## 8.8 Thứ tự

Read-only tools trước, action tools sau.

Tạo:

```text
reports/upgrade/05_agent_tools.md
```

---

# 9. PHASE 5 — KNOWLEDGE VÀ MEMORY

## 9.1 Knowledge schema

```text
source_id
title
version
effective_date
expiry_date
issuing_unit
document_type
access_scope
checksum
content
```

## 9.2 Retrieval

Trả evidence + metadata. Không nhét toàn corpus vào system prompt.

## 9.3 Dynamic data

Dùng tool cho schedule, announcement, appointment, personal status và ticket.

## 9.4 Session memory

Giữ 6–8 recent turns. Summary theo message/token threshold. Bảo toàn unfinished task và tool sequence.

## 9.5 Long-term preference

Chỉ lưu sau explicit consent. Có read/delete/clear/disable.

Tạo:

```text
reports/upgrade/06_knowledge_and_memory.md
```

---

# 10. PHASE 6 — ROBOT EXPRESSION

## 10.1 Behavior IDs

```text
attentive_idle
gentle_nod
happy_tilt
slow_nod
soft_nod
positive_nod
attentive_still
```

## 10.2 Mapping

Map style → behavior. Không raw servo.

## 10.3 ACK

Behavior command có ACK/failure.

## 10.4 Interruption

Barge-in cancel stale speech và stale queued behavior phù hợp.

Tạo:

```text
reports/upgrade/07_robot_expression.md
```

---

# 11. SECURITY VÀ PRIVACY

Kiểm tra:

- secret trong Git;
- token trong log;
- token trong frontend;
- cross-session context;
- cross-user memory;
- unauthorized tools;
- prompt injection;
- unsafe robot command;
- missing confirmation;
- false success.

Test chứng minh:

```text
permission enforce ngoài LLM
retrieved text không tự cấp quyền
session A không đọc session B
```

Tạo:

```text
SECURITY_REVIEW.md
```

---

# 12. TEST BẮT BUỘC

## 12.1 Unit

- config;
- profile;
- fallback;
- router schema;
- style validation;
- chunking;
- glossary;
- task state;
- confirmation;
- tool result;
- summarization;
- secret mask.

## 12.2 Integration

- STT → LLM;
- routing;
- tool call/result;
- Response Composer;
- Expression Composer;
- TTS adapter;
- fallback;
- cancellation;
- reconnect;
- isolation.

## 12.3 Mic thật

Test:

```text
microphone
→ STT
→ LLM
→ TTS
→ speaker
```

Câu bắt buộc:

```text
“Bạn là ai?”
“Tên tôi là Minh Hiếu.”
“Tôi vừa nói tên gì?”
“Ngày mai nhắc tôi nộp báo cáo lúc chín giờ.”
“Hãy soạn một email xin lịch gặp, nhưng chưa gửi.”
“Dừng lại.”
```

Xác minh user transcript không bị đưa nhầm vào assistant TTS.

## 12.4 Soak

```text
30 phút
≥30 turn
≥10 barge-in
≥5 reconnect
≥3 LLM timeout
≥3 TTS failure
```

Theo dõi memory, file descriptors, queue, stale audio, orphan process.

## 12.5 Capacity

```text
1 session
2 sessions
4 control-plane sessions
```

Chỉ chạy 4 full inference nếu tài nguyên cho phép.

---

# 13. NĂM VÒNG REVIEW

## Vòng 1 — Architecture

- Pipecat API;
- transport lifecycle;
- provider abstraction;
- Flow state;
- không phình kiến trúc.

## Vòng 2 — Vietnamese voice

- STT;
- VAD;
- glossary;
- VieNeu;
- chunking;
- Piper fallback;
- emotion metadata.

## Vòng 3 — Agent

- routing;
- task state;
- tools;
- confirmation;
- retry;
- verification;
- no false success.

## Vòng 4 — Security

- secret;
- permission;
- injection;
- isolation;
- memory;
- robot safety.

## Vòng 5 — Production readiness

- lock file;
- model revision;
- docs;
- install;
- restart;
- metrics;
- capacity;
- limitation.

Ghi riêng từng vòng vào:

```text
CHANGELOG_REVIEW.md
```

Không copy cùng một nội dung cho năm vòng.

---

# 14. OUTPUT BẮT BUỘC

Tạo/cập nhật:

```text
FINAL_STATUS.md
ARCHITECTURE.md
CONFIGURATION.md
MODEL_INVENTORY.md
LICENSE_INVENTORY.md
DEPENDENCY_LOCK_REPORT.md
STT_BENCHMARK_REPORT.md
TTS_BENCHMARK_REPORT.md
LLM_GATEWAY_CAPABILITY_REPORT.md
AGENT_TOOL_REPORT.md
KNOWLEDGE_MEMORY_REPORT.md
SECURITY_REVIEW.md
LOCAL_MIC_ACCEPTANCE.md
LATENCY_REPORT.md
CAPACITY_REPORT.md
KNOWN_LIMITATIONS.md
CHANGELOG_REVIEW.md
TEST_EVIDENCE.md
HUMAN_TASK_CHECKLIST.md
```

**HUMAN_TASK_CHECKLIST.md** gom mọi việc bắt buộc cần con người thật, mỗi mục có: mô tả, cách thực hiện từng bước, tiêu chí đạt, gate nào đang chờ nó. Tối thiểu phải phủ:

```text
- Test mic thật (mục 12.3) với các câu bắt buộc
- Nghe và đánh giá audio output từng TTS profile
- Thu corpus STT vòng 2 (spec 23.1: 6 người, 3 miền)
- Panel người nghe A/B ≥8 người (spec 23.2a)
- Soak 30 phút với reconnect vật lý
- Xác nhận tên persona với nhà trường
- Legal review license/voice trước phân phối
```

Artifacts:

```text
artifacts/upgrade/environment.txt
artifacts/upgrade/python-tests.txt
artifacts/upgrade/frontend-tests.txt
artifacts/upgrade/frontend-build.txt
artifacts/upgrade/stt-results.json
artifacts/upgrade/tts-results.json
artifacts/upgrade/runtime-metrics.jsonl
artifacts/upgrade/latency-report.txt
artifacts/upgrade/security-scan.txt
artifacts/upgrade/soak.log
artifacts/upgrade/capacity-report.txt
```

---

# 15. QUY TẮC FINAL STATUS

Báo cáo phải bắt đầu:

```text
FINAL UPGRADE STATUS: PASS / PARTIAL / FAIL
```

Mỗi tiêu chí chỉ dùng:

```text
PASS
FAIL
NOT RUN
BLOCKED
```

Không báo PASS khi:

- mic thật chưa test;
- model chưa tải;
- audio chưa nghe;
- endpoint chưa gọi;
- tool backend chưa có;
- capacity chưa test;
- emotion chưa có listener evaluation.

**Kỳ vọng thực tế:** vì nhiều gate phụ thuộc con người, kết quả đúng đắn của một phiên agent gần như luôn là `PARTIAL` kèm HUMAN_TASK_CHECKLIST.md đầy đủ. Một báo cáo `PARTIAL` trung thực với checklist rõ ràng có giá trị hơn một báo cáo `PASS` bịa — `PASS` toàn phần chỉ hợp lệ sau khi con người hoàn thành checklist và cập nhật evidence.

---

# 16. FORMAT PHẢN HỒI CUỐI

Cuối quá trình, trả:

1. Final status.
2. Kiến trúc đã triển khai.
3. File thay đổi.
4. Model và revision.
5. Test count.
6. Mic evidence.
7. Quyết định STT.
8. Quyết định TTS.
9. Tool đã làm.
10. Confirmation/safety evidence.
11. Latency.
12. Capacity.
13. Blocker.
14. Lệnh tái lập.
15. ZIP hoặc patch nếu môi trường hỗ trợ.

Không dừng ở kế hoạch. Triển khai tối đa trong môi trường hiện tại, đánh dấu blocker ngoài môi trường và để repository ở trạng thái có thể tái lập.
