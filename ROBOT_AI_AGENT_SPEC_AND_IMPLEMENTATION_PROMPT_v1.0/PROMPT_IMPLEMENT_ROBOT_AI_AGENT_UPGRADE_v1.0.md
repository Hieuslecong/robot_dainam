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
ROBOT_AI_AGENT_MASTER_SPECIFICATION_v1.0.md
```

Đọc toàn bộ tài liệu trên trước khi thay đổi code.

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

---

# 3. AUDIT BAN ĐẦU

Chạy và lưu:

```bash
pwd
git status --short
find . -maxdepth 3 -type f | sort
python3 --version
uv --version
node --version
npm --version
uname -a
uname -m
```

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

Thay persona lặp/xung đột bằng:

```text
Tên: N.E.K.O
Bản chất: trợ lý AI
Vai trò: đồng hành học tập, tra cứu và hỗ trợ công việc cá nhân
Tính cách: ấm áp, điềm tĩnh, chủ động nhưng không áp đặt
Xưng hô: mình – bạn
```

Không dùng câu boilerplate:

```text
“Tôi là trợ lý nhà trường, sẵn sàng hỗ trợ...”
```

Câu trả lời định danh mong muốn:

```text
“Mình là N.E.K.O, trợ lý AI đồng hành của trường. Mình có thể giúp bạn tra cứu thông tin, sắp xếp công việc hoặc xử lý một số tác vụ trong trường.”
```

Rút ngắn core prompt. Chuyển hard length policy sang processor khi phù hợp.

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

```bash
uv run pytest -q
npm ci --prefix clients/browser
npm run test --prefix clients/browser
npm run build --prefix clients/browser
```

Tạo:

```text
reports/upgrade/01_foundation_cleanup.md
```

---

# 5. PHASE 1 — STT TIẾNG VIỆT

## 5.1 Profile

Tạo:

```text
stt_fast_vi
stt_balanced_vi
stt_accurate_vi
stt_research_vi
```

Mapping ứng viên:

```text
stt_fast_vi:
Whisper large-v3-turbo q4 hiện tại

stt_balanced_vi:
Whisper large-v3-turbo 8-bit MLX

stt_accurate_vi:
PhoWhisper-medium hoặc runtime conversion đã xác minh

stt_research_vi:
Whisper large-v3 8-bit MLX
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

Nếu chưa có audio thật, tạo schema và đánh dấu runtime benchmark `BLOCKED`; không tạo số giả.

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

Không tự chọn PhoWhisper hoặc 8-bit.

Ứng viên ban đầu ưu tiên:

```text
Whisper large-v3-turbo 8-bit
```

nhưng benchmark quyết định.

Tạo:

```text
reports/upgrade/02_stt_benchmark.md
artifacts/upgrade/stt-results.json
```

---

# 6. PHASE 2 — LOCAL EXPRESSIVE TTS

## 6.1 Profile

Tạo:

```text
expressive_local_vi
lightweight_local_vi
fallback_local_vi
```

Mapping:

```text
expressive_local_vi:
VieNeu expressive local model

lightweight_local_vi:
VieNeu 0.3B quantized

fallback_local_vi:
Piper HTTP vi_VN-vais1000-medium
```

Không xóa Piper hiện tại.

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

```text
naturalness ≥4.2/5
preference over Piper ≥80%
emotion correctness ≥85%
proper-name pronunciation ≥95%
TTFA P50 ≤500 ms
barge-in stop P95 ≤250 ms
```

Nếu expressive model chậm trên M1, giữ quality profile và dùng light profile làm mặc định.

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

Fast model:

- greeting;
- small talk;
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

```text
search_school_knowledge
get_school_schedule
find_school_form
get_deadline
get_contact_information
create_note
create_reminder
list_calendar_events
create_calendar_event
draft_email
send_email
create_support_ticket
set_robot_behavior
show_screen_content
```

Nếu backend thật chưa có, tạo adapter interface và test fake. Không dùng fake làm bằng chứng production.

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
