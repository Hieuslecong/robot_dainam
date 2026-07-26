# ROBOT AI AGENT — MASTER TECHNICAL SPECIFICATION

> **Document ID:** RAA-MTS-1.1  
> **Version:** 1.1  
> **Status:** Proposed implementation baseline  
> **Changelog v1.1:** Sửa mâu thuẫn latency budget (mục 17); thêm ràng buộc Router nhanh (9.8); thêm ứng viên STT streaming (8.1); kiến trúc TTS hai tầng + tier cloud tùy chọn (16); hạ scope action tools MVP (11, 22); bổ sung nguồn dữ liệu benchmark và panel người nghe (23); thêm wake/idle và lọc người nói chính (8.7); ghi chú xác nhận persona (9.4)  
> **Primary language:** Vietnamese  
> **Development target:** macOS Apple Silicon M1  
> **Optional production acceleration:** Linux/NVIDIA  
> **Voice framework:** Pipecat 1.6.0  
> **Repository:** `robot-ai-host`

---

# 1. MỤC TIÊU TÀI LIỆU

Tài liệu này là nguồn đặc tả chính thức để nâng cấp hệ thống `robot-ai-host` từ một voice chatbot thành một realtime agent tiếng Việt thông minh, biểu cảm và hỗ trợ nhiều tác vụ.

Hệ thống hiện tại:

```text
Microphone
→ SmallWebRTC
→ Pipecat
→ Whisper STT local
→ OpenAI-compatible LLM gateway
→ Piper TTS local
→ Speaker
```

Hệ thống mục tiêu:

```text
Realtime Vietnamese Agent
=
Voice realtime
+ STT tiếng Việt chính xác
+ LLM routing thích ứng
+ Agent Orchestrator
+ Pipecat Flows
+ Typed Tool Gateway
+ Knowledge có nguồn
+ Memory có kiểm soát
+ TTS local biểu cảm
+ Hành vi robot hợp lệ
+ Xác nhận, ACK và audit
```

Không viết lại FastAPI, Pipecat, SmallWebRTC, RTVI, session isolation hoặc provider-profile architecture nếu không có lỗi đã được chứng minh bằng test.

---

# 2. KẾT LUẬN KIẾN TRÚC CHỐT

```text
CORE
Pipecat 1.6.0
FastAPI
SmallWebRTC
RTVI
Silero VAD
Smart Turn

STT MẶC ĐỊNH ỨNG VIÊN
Whisper large-v3-turbo 8-bit trên MLX

STT ĐỐI CHỨNG CHÍNH XÁC
PhoWhisper-medium

STT ỨNG VIÊN LATENCY (STREAMING)
VietASR/Zipformer qua sherpa-onnx — transcribe trong khi nói

STT FALLBACK
Whisper large-v3-turbo q4 hiện tại

LLM
OpenAI-compatible gateway thay đổi qua .env
Router: heuristic bypass trước, model cực nhỏ sau — budget riêng ≤300 ms
Conversation/tool executor model
Planner model chỉ dùng khi tác vụ phức tạp

AGENT
Một Agent Orchestrator
Pipecat function calling
Pipecat Flows
Typed Tool Gateway

KNOWLEDGE
Tài liệu có nguồn, version và ngày hiệu lực
Dữ liệu động lấy qua API/tool

MEMORY
6–8 lượt gần nhất
Context summarization
Task state riêng
Long-term preference chỉ lưu khi người dùng đồng ý

TTS KIẾN TRÚC HAI TẦNG
Tầng mở màn: Piper (TTFA thấp) phát câu/ack đầu tiên
Tầng biểu cảm: VieNeu expressive render các câu tiếp theo
trong khi câu đầu đang phát (che độ trễ bằng playback)

TTS NHẸ
VieNeu-TTS 0.3B quantized

TTS CLOUD TÙY CHỌN (PLAN B BIỂU CẢM)
Qwen-Audio-3.0-TTS (endpoint Singapore) — profile opt-in khi có mạng,
dùng nếu VieNeu trượt gate trên M1

TTS FALLBACK
Piper HTTP

BIỂU CẢM
Response Composer
Expression Composer
Prosody-aware chunking
Validated robot behavior

AN TOÀN
Confirmation
Permission enforcement ngoài LLM
Tool ACK
Audit
Session isolation
```

Mọi model chỉ trở thành mặc định sau khi vượt qua benchmark gate trong tài liệu này.

---

# 3. ĐÁNH GIÁ HIỆN TRẠNG

## 3.1 Điểm mạnh

1. Kiến trúc voice realtime đã hình thành.
2. SmallWebRTC và Pipecat phù hợp với browser và robot.
3. Provider profile cho phép đổi STT, LLM và TTS.
4. Endpoint, token và model LLM có thể đổi bằng biến môi trường.
5. STT và TTS local giúp giảm chi phí và tăng riêng tư.
6. Đã có VAD, Smart Turn, barge-in, session, JWT và metrics.
7. Piper đủ nhanh để giữ làm fallback.
8. Browser có thể đóng vai thiết bị thật trước khi tích hợp robot.

## 3.2 Điểm yếu chặn mục tiêu

### STT

- `whisper-large-v3-turbo-q4` chưa đủ chính xác với dấu tiếng Việt.
- Có nguy cơ cắt âm cuối do VAD/turn timing.
- Echo từ loa có thể đi ngược vào microphone.
- Tên riêng, mã sinh viên, số, ngày và Việt–Anh chưa được bảo vệ.
- Độ trễ STT hiện còn cao.

### LLM và persona

- Persona hiện tại lặp và xung đột vai trò.
- Văn phong hành chính, lặp “sẵn sàng hỗ trợ”.
- Một model đang gánh router, executor, planner và persona cùng lúc.
- Chưa có tool nghiệp vụ và task state.
- Context có nguy cơ tăng không giới hạn.
- Chưa tách “trả lời bằng lời” khỏi “hành động đã được thực hiện”.

### TTS

- Piper ổn định nhưng đơn điệu.
- Không có điều khiển cảm xúc thực.
- Sentence-level chunking có thể reset prosody quá thường xuyên.
- Văn bản LLM hiện tại vốn đã cứng.
- Chưa có schema biểu cảm chung.

### Agent

- Chưa có tool lookup nghiệp vụ.
- Chưa có calendar, reminder, email, support ticket.
- Chưa có confirmation gate.
- Chưa có task continuation.
- Knowledge mới là placeholder.
- Chưa có memory lifecycle do người dùng kiểm soát.

### Vận hành

- Có nguy cơ trùng nguồn config.
- Dependency cần pin đầy đủ.
- Metrics chưa giải thích hết E2E delay.
- Chưa chứng minh bốn phiên inference thật.
- License và quyền phân phối model/voice cần rà soát.

---

# 4. MỤC TIÊU SẢN PHẨM

Agent sau nâng cấp phải:

1. Hiểu tiếng Việt tự nhiên ở nhiều vùng miền.
2. Xử lý tốt tên, số, ngày, mã và từ chuyên môn.
3. Trả lời ngắn, tự nhiên, không hành chính.
4. Có cảm xúc đúng ngữ cảnh nhưng không diễn quá mức.
5. Thực hiện tác vụ thật thay vì chỉ sinh văn bản.
6. Tra cứu thông tin trường học có nguồn.
7. Giữ ngữ cảnh và task đang làm dở.
8. Xin xác nhận trước hành động quan trọng.
9. Chỉ báo hoàn tất sau khi tool trả ACK hợp lệ.
10. Chạy được một profile hữu ích trên Mac M1.
11. Có thể chuyển inference nặng sang server GPU mà không viết lại agent core.
12. Hỗ trợ browser làm thiết bị kiểm thử thật.

---

# 5. PHẠM VI KHÔNG THỰC HIỆN TRONG MVP

1. Không xây multi-agent swarm.
2. Không triển khai Kubernetes.
3. Không tách mọi module thành microservice.
4. Không lưu vô thời hạn toàn bộ transcript.
5. Không cho LLM sinh lệnh motor thô.
6. Không triển khai vector database trước retrieval evaluation.
7. Không hỗ trợ thanh toán hoặc hành động tài chính.
8. Không tuyên bố four-device ready nếu chưa test.
9. Không thay Pipecat/WebRTC khi chưa có lỗi xác nhận.
10. Không coi emotion tag là thay thế cho TTS có năng lực.
11. Không báo thành công trước tool ACK.

---

# 6. KIẾN TRÚC MỤC TIÊU

```text
┌────────────────────────────────────────────┐
│ Browser / Robot                            │
│ Microphone · Speaker · Display tùy chọn    │
└───────────────────┬────────────────────────┘
                    │ SmallWebRTC + RTVI
┌───────────────────▼────────────────────────┐
│ Realtime Interaction Layer                 │
│ Audio capture · AEC · VAD · Smart Turn     │
│ Barge-in · STT provider routing            │
└───────────────────┬────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ Intent · Complexity · Risk Router          │
│ small talk · lookup · action · sensitive   │
└───────────┬────────────────────┬───────────┘
            │                    │
      direct dialogue      structured workflow
            │                    │
┌───────────▼───────────┐  ┌────▼─────────────────┐
│ Conversation Executor│  │ Agent Orchestrator   │
│ short response       │  │ Pipecat Flows        │
│ read-only tool       │  │ task state           │
└───────────┬───────────┘  │ confirmation         │
            │              │ retry/verification   │
            │              └────┬─────────────────┘
            │                   ↓
            │        ┌────────────────────────────┐
            │        │ Typed Tool Gateway         │
            │        │ School · Calendar · Email  │
            │        │ Reminder · Support · Robot │
            │        └─────────────┬──────────────┘
            └──────────────────────┤
                                   ↓
┌────────────────────────────────────────────┐
│ Knowledge and Memory                       │
│ source-aware retrieval · dynamic APIs      │
│ recent context · summary · task state      │
└───────────────────┬────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ Response Composer                          │
│ natural, concise spoken Vietnamese         │
└───────────────────┬────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ Expression Composer                        │
│ text · emotion · intensity · rate · action │
└───────────────────┬────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ TTS Router                                 │
│ VieNeu expressive → VieNeu light → Piper   │
└───────────────────┬────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ Speaker + Validated Robot Behavior         │
└────────────────────────────────────────────┘
```

---

# 7. NGUYÊN TẮC THIẾT KẾ

## 7.1 Provider-independent

STT, LLM và TTS phải được chọn theo profile và khởi tạo qua provider factory.

## 7.2 Một orchestrator trước

MVP dùng một orchestrator và nhiều tool nhỏ. Chỉ tách specialist agent khi có prompt lớn, quyền riêng, lifecycle dài hoặc Flow không còn đủ.

## 7.3 State tường minh

Task state lưu bằng schema, không suy luận lại từ transcript dài.

## 7.4 Verification thay cho niềm tin

Agent không được tin rằng hành động thành công chỉ vì LLM sinh câu khẳng định.

## 7.5 Progressive capability

```text
làm sạch nền tảng
→ nâng voice
→ read-only tools
→ action tools
→ memory
→ multi-device
```

## 7.6 Fallback bắt buộc

Mỗi thành phần realtime chính phải có degraded mode.

---

# 8. ĐẶC TẢ STT

## 8.1 Profile

### `stt_fast_vi`

- Model: Whisper large-v3-turbo q4 hiện tại.
- Vai trò: fallback hoặc máy thiếu RAM.

### `stt_balanced_vi`

- Model: Whisper large-v3-turbo 8-bit MLX.
- Vai trò: ứng viên mặc định cho Apple Silicon.

### `stt_accurate_vi`

- Model: PhoWhisper-medium hoặc runtime chuyển đổi đã xác minh.
- Vai trò: đối chứng chuyên tiếng Việt.

### `stt_research_vi`

- Model: Whisper large-v3 8-bit MLX.
- Vai trò: so sánh độ chính xác cao.

### `stt_streaming_vi`

- Model: VietASR/Zipformer (streaming, sherpa-onnx runtime).
- Vai trò: ứng viên giải quyết latency tận gốc — transcribe song song khi người dùng còn nói, speech-end → final gần tức thời.
- Lý do bắt buộc có mặt: các profile họ Whisper là batch — 8-bit **nặng hơn q4** nên speech-end → final sẽ **chậm hơn hiện trạng ~1.9 s**, gần như chắc chắn trượt gate ≤900 ms trên M1. Nếu benchmark xác nhận điều đó, streaming là đường duy nhất đạt gate latency mà không hy sinh accuracy.
- Đánh đổi chấp nhận: công tích hợp cao hơn (runtime riêng), cần xác minh chất lượng dấu tiếng Việt trên corpus trước khi làm mặc định.

## 8.2 Quy tắc chọn model

Không chọn theo cảm giác. Chấm theo:

```text
semantic accuracy
proper-name accuracy
number/date accuracy
silent hallucination
speech-end latency
RAM
hai phiên đồng thời
```

## 8.3 Glossary

Tạo glossary versioned cho:

- tên trường;
- khoa/phòng ban;
- tòa nhà/phòng;
- tên người;
- từ viết tắt;
- chương trình đào tạo;
- thuật ngữ Việt–Anh.

Glossary correction phải lưu transcript gốc, transcript sửa và confidence. Không sửa khi confidence thấp.

## 8.4 Xác nhận trường quan trọng

Agent phải xác nhận nếu STT không chắc chắn với:

- mã sinh viên;
- email;
- ngày/giờ;
- tên người;
- phòng;
- số điện thoại;
- mã biểu mẫu.

## 8.5 VAD và AEC

- Tune VAD bằng recordings thật.
- Kiểm tra âm đầu, âm cuối, câu ngắn, nói nhanh và barge-in.
- Xác minh browser đang bật `echoCancellation`, `noiseSuppression`, `autoGainControl` trước khi xây AEC server.

## 8.6 Gate STT

| Chỉ tiêu | Mục tiêu |
|---|---:|
| Semantic accuracy | ≥95% |
| Tên trong glossary | ≥95% |
| Trường quan trọng sau xác nhận | ≥99% |
| Hallucination khi im lặng | <0,5% |
| Speech end → final P50 | ≤900 ms |
| Hai phiên trên Mac mục tiêu | Ổn định |
| Cross-session transcript leakage | 0 |

Ghi chú gate latency: đo speech-end → final theo từng profile; nếu mọi profile batch Whisper trượt ≤900 ms trên phần cứng mục tiêu, `stt_streaming_vi` trở thành ứng viên mặc định bắt buộc phải benchmark trước khi kết luận Phase 1.

## 8.7 Chế độ kích hoạt và môi trường công cộng

Robot đặt tại sảnh trường — môi trường nhiều người nói, trẻ em, tiếng ồn nền, câu nói vãng lai không hướng vào robot. Bắt buộc:

- **Idle/active state**: robot ở trạng thái idle không đưa audio vào LLM; chuyển active bằng wake word, nút bấm/chạm màn hình, hoặc phát hiện người đứng đối diện (nếu có cảm biến). MVP tối thiểu: nút bấm hoặc chạm màn hình.
- **Lọc người nói chính**: chỉ xử lý nguồn âm chủ đạo; câu nói chồng lấn hoặc quá nhỏ so với người nói chính bị loại ở STTGuard. Không yêu cầu diarization đầy đủ trong MVP — chỉ cần ngưỡng năng lượng + khoảng cách thời gian.
- **Timeout về idle**: không có lượt nói hợp lệ trong N giây (mặc định 30 s) → tự về idle, xóa context phiên vãng lai.
- Test bắt buộc: phát audio hội thoại nền không hướng vào robot trong trạng thái idle — robot không được phản hồi.

---

# 9. ĐẶC TẢ LLM VÀ ROUTING

## 9.1 Cấu hình endpoint

Bắt buộc giữ:

```env
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
LLM_DEFAULT_HEADERS_JSON=
LLM_TIMEOUT_SECONDS=
```

Không hard-code endpoint, token hoặc model.

Có thể bổ sung:

```env
LLM_ROUTER_MODEL=
LLM_EXECUTOR_MODEL=
LLM_PLANNER_MODEL=
```

Nếu không có, fallback về `LLM_MODEL`.

## 9.2 Vai trò model

### Router

- intent;
- complexity;
- risk;
- confidence;
- direct path hoặc Flow;
- field extraction ban đầu.

### Conversation executor

- small talk;
- knowledge answer;
- simple read-only tools;
- spoken response.

### Planner

- tác vụ nhiều bước;
- nhiều tool;
- error recovery;
- yêu cầu mơ hồ;
- tổng hợp phức tạp.

Planner không chạy cho chào hỏi hoặc lookup một bước.

## 9.3 Capability probe

Mỗi model phải được test:

```text
non-stream
stream
function calling
structured output
tool_choice
reasoning_content
cancellation
timeout
empty content
```

Model chỉ trả `reasoning_content` mà không có nội dung dùng được không được đặt trực tiếp trong voice path.

## 9.4 Persona

```text
Tên: N.E.K.O
Bản chất: trợ lý AI
Vai trò: đồng hành học tập, tra cứu và hỗ trợ công việc cá nhân
Tính cách: ấm áp, điềm tĩnh, chủ động nhưng không áp đặt
Xưng hô: mình – bạn
```

Khi hỏi “Bạn là ai?” có thể trả:

> Mình là N.E.K.O, trợ lý AI đồng hành của trường. Mình có thể giúp bạn tra cứu thông tin, sắp xếp công việc hoặc xử lý một số tác vụ trong trường.

⚠️ Tên "N.E.K.O" là quyết định branding, không phải quyết định kỹ thuật — phải được phía nhà trường xác nhận trước khi hard-code vào prompt/UI. Cho đến khi xác nhận, tên persona đọc từ config (`PERSONA_NAME`), không viết cứng trong source.

## 9.5 Quy tắc văn phong

- Trả lời trực tiếp.
- Không dùng văn hành chính.
- Không lặp “sẵn sàng hỗ trợ”.
- Không nhắc lại câu hỏi trừ khi xác nhận.
- Không giả là con người.
- Độ dài thay đổi theo intent.
- Đồng cảm đúng ngữ cảnh.
- Không đọc Markdown, URL, metadata.

## 9.6 Temperature

```text
Router/extraction: 0.0–0.2
Planner: 0.1–0.3
Conversation: 0.45–0.6
Response Composer: 0.4–0.55
```

## 9.7 Prompt budget

- Core persona/safety: 500–800 tokens.
- Flow node instruction: 100–300 tokens.
- Chỉ đưa tool liên quan node hiện tại.

## 9.8 Ràng buộc Router (bắt buộc)

Router là vòng gọi nối tiếp đứng trước executor — nếu chậm, nó nhân đôi độ trễ của mọi lượt nói. Quy tắc cứng:

1. **Budget riêng: router P50 ≤300 ms** (đo từ stt_final → router decision). Vượt budget này thì router bị coi là fail bất kể độ chính xác.
2. **Heuristic bypass trước LLM**: greeting, câu quá ngắn, mẫu small talk phổ biến, lệnh dừng — phân loại bằng rule/regex/keyword local, **không gọi LLM router**. Mục tiêu ≥60% lượt nói thông thường đi đường bypass.
3. Khi phải gọi LLM router: dùng model nhỏ nhất có structured output đạt yêu cầu (`LLM_ROUTER_MODEL`), max_tokens tối thiểu, không streaming.
4. Router timeout ⇒ fallback thẳng vào conversation executor với intent `unclear`; không được chặn turn.
5. Metrics phải tách riêng `router_latency` và `router_bypass_rate` trong timeline mục 17.

## 10.1 Intent taxonomy

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

## 10.2 Risk taxonomy

```text
read_only
low_risk_write
confirmed_write
sensitive
unsupported
```

## 10.3 Direct path

Dùng cho:

- chào hỏi;
- small talk;
- câu trả lời ngắn;
- read-only lookup một bước;
- clarification đơn giản.

## 10.4 Structured Flow

Dùng khi:

- thiếu trường bắt buộc;
- nhiều tool;
- cần xác nhận;
- có retry;
- ghi dữ liệu;
- tiếp tục task dở;
- tác vụ nhạy cảm.

## 10.5 Task state

```text
task_id
session_id
user_id
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
created_at
updated_at
status
```

Status:

```text
created
collecting
awaiting_confirmation
executing
completed
failed
cancelled
expired
```

## 10.6 Confirmation

Bắt buộc trước:

- gửi email;
- tạo/sửa lịch;
- tạo phiếu;
- nộp biểu mẫu;
- xóa dữ liệu;
- hành động thiết bị bảo vệ.

## 10.7 Kết quả thật

Chỉ báo thành công khi tool trả `success` và có ACK cần thiết.

---

# 11. TYPED TOOL GATEWAY

## 11.1 Tool MVP

### Read-only

```text
search_school_knowledge
get_school_schedule
find_school_form
get_deadline
get_contact_information
```

### Personal

```text
create_note
create_reminder
list_calendar_events
```

### Action — MVP (backend thật, bắt buộc)

```text
create_reminder        # backend local, kiểm chứng được thật
draft_email            # chỉ soạn, không gửi — không cần backend email thật
```

### Action — interface-only trong MVP (adapter + fake test, KHÔNG tính vào acceptance)

```text
create_calendar_event
send_email
create_support_ticket
```

Lý do tách: acceptance "zero unauthorized action / zero false success" chỉ có giá trị khi test trên backend thật. Test trên fake adapter chứng minh contract đúng, không chứng minh hệ thống an toàn — không được dùng làm bằng chứng nghiệm thu. Các tool interface-only chuyển sang MVP+1 khi trường cung cấp backend.

### Robot

```text
set_robot_behavior
show_screen_content
```

## 11.2 Contract bắt buộc

Mỗi tool có:

- input schema;
- output schema;
- permission;
- confirmation requirement;
- timeout;
- retry;
- idempotency;
- audit fields;
- error codes.

## 11.3 Result envelope

```json
{
  "tool_call_id": "string",
  "tool_name": "string",
  "status": "success|partial|failed|timeout|denied",
  "data": {},
  "message": "sanitized result",
  "error_code": null,
  "retryable": false,
  "timestamp": "ISO-8601"
}
```

## 11.4 Bảo mật tool

- Permission enforce ngoài LLM.
- Resolve identity trước protected action.
- LLM không nhận credential thô.
- Validate input sau extraction.
- Sanitize output trước context.
- Retrieved text không được tự cấp quyền.

---

# 12. KNOWLEDGE

## 12.1 Fixed policy

Chỉ giữ phần ngắn trong prompt:

- identity;
- safety;
- scope;
- response style;
- confirmation policy.

## 12.2 Tài liệu trường học

Metadata:

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
```

## 12.3 Dữ liệu động

Lấy qua tool:

- lịch học;
- lịch hẹn;
- thông báo mới;
- trạng thái hồ sơ;
- trạng thái ticket.

## 12.4 Retrieval output

```text
answer evidence
source title
source version
effective date
relevance score
retrieval timestamp
```

Nếu tài liệu hết hạn hoặc không rõ ngày, agent phải cảnh báo có thể cũ.

---

# 13. MEMORY

## 13.1 Session memory

Giữ 6–8 lượt gần nhất.

## 13.2 Context summarization

Kích hoạt khi vượt message/token threshold hoặc task hoàn tất.

Summary phải giữ:

- preference liên quan;
- câu hỏi chưa giải quyết;
- active task;
- facts đã xác nhận;
- tool result cần tiếp tục.

## 13.3 Long-term preference

Chỉ lưu sau consent:

- tên gọi;
- cách xưng hô;
- giọng yêu thích;
- accessibility preference;
- lịch thường dùng.

## 13.4 Control

Cho phép:

- xem memory;
- xóa một mục;
- xóa toàn bộ;
- tắt lưu memory.

## 13.5 Không tự lưu

- password/API key;
- dữ liệu y tế;
- tài chính;
- toàn bộ transcript;
- suy luận thuộc tính nhạy cảm.

---

# 14. RESPONSE COMPOSER

## 14.1 Mục đích

Chuyển agent output và tool result thành lời nói tiếng Việt ngắn, tự nhiên.

## 14.2 Quy tắc

- Kết quả trước.
- Ngôn ngữ đời thường.
- Phân biệt success/partial/failure.
- Một câu hỏi rõ nếu thiếu dữ liệu.
- Dữ liệu dài đưa sang screen payload.

## 14.3 Độ dài

| Intent | Spoken response |
|---|---|
| Greeting | 1 câu |
| Small talk | 1–2 câu |
| Lookup | 1–3 câu |
| Procedure | 3–5 bước ngắn |
| Emotional support | 2–3 câu |
| Confirmation | 1 câu |
| Tool failure | 1–2 câu |
| Complex result | tóm tắt + screen |

---

# 15. EXPRESSION COMPOSER

## 15.1 Schema

```json
{
  "spoken_text": "Mình hiểu rồi. Để mình cùng bạn kiểm tra nhé.",
  "style": "empathetic",
  "intensity": 0.4,
  "speaking_rate": 0.94,
  "pause_profile": "gentle",
  "robot_behavior": "soft_nod",
  "screen_payload": null
}
```

## 15.2 Style allowlist

```text
neutral
friendly
cheerful
calm
empathetic
encouraging
serious
```

Default: `friendly`.

## 15.3 Quy tắc cảm xúc

- Intensity có giới hạn.
- Không dùng cảm xúc mạnh cho thông tin thường.
- Không giả hoảng loạn hoặc thao túng.
- Metadata không được đọc thành lời.
- Unknown style fallback an toàn.

## 15.4 Behavior mapping

```text
neutral → attentive_idle
friendly → gentle_nod
cheerful → happy_tilt
calm → slow_nod
empathetic → soft_nod
encouraging → positive_nod
serious → attentive_still
```

LLM chỉ sinh behavior ID đã validate.

---

# 16. TTS LOCAL BIỂU CẢM

## 16.1 Profile

### `expressive_local_vi`

- VieNeu-TTS expressive local candidate.
- Vai trò: giọng chính nếu đạt gate.

### `lightweight_local_vi`

- VieNeu-TTS 0.3B quantized candidate.
- Vai trò: nhẹ hơn cho M1.

### `fallback_local_vi`

- Piper HTTP `vi_VN-vais1000-medium`.
- Vai trò: uptime/fallback **và tầng mở màn** trong kiến trúc hai tầng (16.2a).

### `cloud_expressive_vi` (tùy chọn — Plan B biểu cảm)

- Qwen-Audio-3.0-TTS qua Alibaba Model Studio, endpoint Singapore.
- Vai trò: profile opt-in khi có mạng, kích hoạt nếu VieNeu (cả expressive lẫn light) trượt gate 16.6 trên phần cứng mục tiêu.
- Ràng buộc: API key qua `.env`; offline ⇒ tự động rơi về chuỗi local; dữ liệu văn bản gửi cloud phải được ghi trong privacy notice.
- Mục đích tồn tại: đảm bảo mục tiêu "biểu cảm" không thất bại toàn phần chỉ vì giới hạn phần cứng M1.

## 16.2 TTS Router — fallback theo lỗi

```text
VieNeu expressive
→ timeout/unavailable/overload
VieNeu light
→ unavailable
Piper
```

(Nếu profile `cloud_expressive_vi` được bật: cloud đứng đầu chuỗi, mất mạng ⇒ rơi về VieNeu.)

## 16.2a Kiến trúc hai tầng — chạy song song theo vai trò (khác với fallback)

Fallback chain xử lý **lỗi**; hai tầng xử lý **độ trễ**. Trong một turn bình thường:

```text
Câu/ack đầu tiên  → Piper (TTFA ~300 ms) → phát ngay
Các câu tiếp theo → VieNeu expressive     → render TRONG KHI câu đầu đang phát
```

Quy tắc:

- Câu đầu do Piper đọc phải ngắn và trung tính (ack, câu dẫn) để chênh lệch giọng giữa hai tầng ít lộ.
- VieNeu bắt đầu render ngay khi có speakable chunk thứ hai, không chờ câu đầu phát xong.
- Nếu VieNeu render xong trước khi câu đầu phát hết ⇒ nối liền mạch; nếu chưa xong ⇒ chấp nhận khoảng lặng ngắn có giới hạn (≤700 ms), quá giới hạn thì câu đó rơi về Piper.
- Turn chỉ có một câu: đi thẳng VieNeu nếu ước lượng render ≤ ngưỡng, ngược lại Piper.
- A/B test phải đo cả cấu hình hai tầng, không chỉ so đơn engine.

## 16.3 Prosody-aware chunking

- Không synthesize token.
- Không phát fragment 2–4 từ không đủ nghĩa.
- Chunk đầu là một ý hoàn chỉnh.
- Ghép câu ngắn cùng cảm xúc.
- Giữ voice/style xuyên một turn.
- Hủy toàn bộ queued audio khi barge-in.

## 16.4 Voice identity

Reference voice phải có consent/license, gồm:

- neutral;
- friendly;
- cheerful;
- empathetic;
- serious;
- Việt–Anh;
- tên riêng và thuật ngữ trường.

## 16.5 Audio

- Giữ native sample rate đến transport boundary.
- Resample một lần.
- Tránh encode/decode lặp.
- Loudness nhất quán.
- Không clipping.

## 16.6 Gate TTS

| Chỉ tiêu | Mục tiêu |
|---|---:|
| Naturalness | ≥4,2/5 |
| Ưu tiên hơn Piper | ≥80% |
| Emotion đúng | ≥85% |
| Tên riêng đúng | ≥95% |
| Audio lỗi/bỏ từ | <1% |
| TTFA P50 — audio đầu tiên nghe được của turn (tầng mở màn) | ≤500 ms |
| Khoảng lặng giữa tầng mở màn và tầng biểu cảm P95 | ≤700 ms |
| Barge-in audible stop P95 | ≤250 ms |
| Đọc metadata/tag | 0 |
| Voice consistency trong một tầng | ≥90% |

Gate TTFA áp cho **âm thanh đầu tiên người dùng nghe được**, không áp cho engine biểu cảm đứng riêng — engine biểu cảm được phép chậm hơn miễn là bị che bởi playback của tầng mở màn (16.2a). Nếu cả kiến trúc hai tầng vẫn trượt gate trải nghiệm, kích hoạt `cloud_expressive_vi` làm Plan B trước khi kết luận Phase 1 thất bại.

---

# 17. LATENCY VÀ METRICS

## 17.1 Timeline chuẩn

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

## 17.2 Mô hình chồng lấn (bắt buộc hiểu trước khi đọc target)

Các chặng KHÔNG cộng tuần tự. Quan hệ chồng lấn bắt buộc:

```text
TUẦN TỰ (critical path):
speech_end → stt_final → [router ≤300ms hoặc bypass ~0ms] → llm_first_token
           → first_speakable_chunk → tts_first_audio → client_audible_start

CHỒNG LẤN (không nằm trên critical path):
- STT streaming (nếu dùng): transcribe TRONG khi nói ⇒ speech_end → stt_final ≈ 0–200 ms
- TTS tầng mở màn synthesize speakable chunk đầu NGAY khi có, trong khi LLM còn stream phần sau
- TTS tầng biểu cảm render câu 2+ TRONG khi câu 1 đang phát
- Tool call chạy song song với câu ack ("Để mình kiểm tra nhé") đang phát
```

## 17.3 Ngân sách critical path — hai kịch bản

**Kịch bản A — STT batch (Whisper), đường bypass router:**

| Chặng | Target P50 |
|---|---:|
| speech_end → stt_final | ≤900 ms |
| router (bypass) | ~0 ms |
| stt_final → llm_first_token | ≤700 ms |
| first_token → first_speakable_chunk | ≤400 ms |
| speakable_chunk → tts_first_audio (tầng mở màn) | ≤500 ms |
| **E2E: user stop → audible P50** | **≤2,6 s** |

**Kịch bản B — STT streaming, đường bypass router:**

| Chặng | Target P50 |
|---|---:|
| speech_end → stt_final | ≤200 ms |
| router (bypass) | ~0 ms |
| stt_final → llm_first_token | ≤700 ms |
| first_token → first_speakable_chunk | ≤400 ms |
| speakable_chunk → tts_first_audio | ≤500 ms |
| **E2E: user stop → audible P50** | **≤1,9 s** |

Khi router phải gọi LLM (không bypass): cộng ≤300 ms vào E2E của kịch bản tương ứng.

**Quy tắc nhất quán:** E2E target của mỗi kịch bản = tổng các chặng critical path của kịch bản đó cộng dự phòng ~100 ms transport. Mọi lần sửa target chặng phải cập nhật lại E2E — không được để bảng tự mâu thuẫn.

## 17.4 Target còn lại

| Metric | Target |
|---|---:|
| Tool acknowledgment P50 | ≤1,5 s |
| Barge-in stop P95 | ≤250 ms |
| router_latency P50 (khi gọi LLM) | ≤300 ms |
| router_bypass_rate | ≥60% |

Phân tách metrics theo small talk, lookup, action workflow và complex planning.

---

# 18. MULTI-SESSION

## 18.1 Development gate

- Một full inference session.
- Sau đó hai concurrent sessions.

## 18.2 Four-device target

Không nạp bốn model lớn độc lập nếu chưa có capacity evidence.

Ưu tiên:

```text
session workers
→ shared STT pool
→ shared TTS pool
```

## 18.3 Resource control

- max sessions;
- max STT jobs;
- max TTS jobs;
- bounded queue;
- timeout/cancel;
- cleanup disconnect;
- warmup state.

---

# 19. SECURITY, PRIVACY VÀ AUDIT

## 19.1 Secret

- `.env` gitignored.
- API key server-side.
- Log mask token/header.
- Frontend bundle không có secret.

## 19.2 Isolation

- Context theo session.
- Task thuộc một user/session.
- Tool result không cross-session.
- Reconnect không phát stale audio.

## 19.3 Audit action

```text
tool_call_id
user_id
session_id
normalized input
confirmation
tool result
timestamp
error
```

## 19.4 Prompt injection

Retrieved content là data, không phải policy. Permission enforce ngoài model.

---

# 20. CONFIG VÀ REPRODUCIBILITY

- Chỉ một config directory chính.
- Loại ambiguity giữa `config/` và `configs/`.
- Pin direct dependencies Python/Node.
- Model có identifier, revision, checksum nếu có.
- Lưu license và nguồn download.

---

# 21. LICENSE

Trước phân phối thương mại phải xác minh:

- Pipecat license;
- STT model license;
- TTS runtime license;
- voice model license;
- quyền sử dụng reference voice;
- quyền redistribution;
- giới hạn generated audio.

Piper tiếp tục chạy sidecar cho đến khi legal review chốt phương thức phân phối.

---

# 22. LỘ TRÌNH TRIỂN KHAI

## Phase 0 — Làm sạch nền tảng

- Một config source.
- Pin dependency.
- Sửa device label.
- Unified metrics.
- Reset conversation.
- Context cap/summarization.
- Persona mới.
- AEC/VAD evidence.
- License inventory.

Gate:

```text
30 phút hội thoại
không context growth mất kiểm soát
không stale audio
metrics đủ timeline
```

## Phase 1 — Voice quality

- Năm STT profile (thêm `stt_streaming_vi`).
- Benchmark vòng 1 trên corpus công khai (VIVOS/Common Voice-vi/VLSP) trước, vòng 2 trên corpus tự thu sau.
- VAD tuning.
- Glossary.
- VieNeu expressive/light + kiến trúc TTS hai tầng (16.2a).
- Piper fallback + tầng mở màn.
- Expression Composer.
- TTS A/B với panel người nghe (23.2a), đo cả cấu hình hai tầng.
- Nếu VieNeu trượt gate: kích hoạt và benchmark `cloud_expressive_vi` trước khi kết luận.

Gate: STT và TTS vượt threshold (gate chủ quan cần panel; chưa có panel = BLOCKED, không phải FAIL).

## Phase 2 — Read-only agent

- Router.
- Knowledge retrieval.
- Nguồn/version.
- Năm read-only tool.
- Task state.
- Confidence handling.

Gate: correct tool ≥95%, không bịa nguồn.

## Phase 3 — Action agent (scope MVP đã hạ — xem 11.1)

- `create_reminder` (backend local thật).
- `draft_email` (soạn, không gửi).
- Confirmation.
- ACK.
- Audit.
- Interface + fake test cho calendar/send_email/support_ticket — KHÔNG tính vào gate.

Gate: zero unauthorized action và zero false success — chỉ chấm trên tool có backend thật. Fake adapter không phải bằng chứng nghiệm thu.

## Phase 4 — Memory

- Recent context.
- Summary.
- Opt-in preference.
- Memory API/UI.
- Delete/disable.

Gate: zero cross-user leakage.

## Phase 5 — Robot và capacity

- Behavior mapping.
- Hai session benchmark.
- Four-session capacity.
- Shared inference nếu cần.
- Soak.
- Deployment hardening.

---

# 23. TEST STRATEGY

## 23.1 STT corpus — hai vòng, không chặn nhau

**Vòng 1 — corpus công khai (không cần thu âm, chạy được ngay):**

- VIVOS, Common Voice-vi, VLSP test set (có ground truth sẵn).
- Mục đích: xếp hạng sơ bộ các STT profile về WER/CER/latency/RAM mà không chờ dữ liệu tự thu.
- Vòng 1 đủ để loại ứng viên yếu; KHÔNG đủ để chốt mặc định.

**Vòng 2 — corpus tự thu (chốt lựa chọn):**

Tối thiểu 200–300 câu:

- Bắc, Trung, Nam;
- nam/nữ;
- nhanh/chậm;
- câu ngắn/dài;
- tên;
- mã sinh viên;
- ngày;
- thuật ngữ trường;
- Việt–Anh;
- noise;
- echo;
- silence.

**Kế hoạch thu âm vòng 2 (bắt buộc lập trước Phase 1):** xác định người thu (tối thiểu 6 người: 2 Bắc, 2 Trung, 2 Nam; cân bằng nam/nữ), thiết bị thu, script câu, thời gian hoàn thành. Đây là công việc con người tính bằng ngày — không được giấu trong một dòng task. Chưa có corpus vòng 2 thì gate STT chỉ được đánh giá "sơ bộ theo vòng 1", không được chốt PASS.

## 23.2 TTS corpus

Tối thiểu 80 câu:

- chào hỏi;
- đồng cảm;
- động viên;
- cảnh báo;
- thủ tục;
- số/ngày;
- tên;
- viết tắt;
- Việt–Anh;
- ngắn/dài.

## 23.2a Panel người nghe (bắt buộc cho mọi gate chủ quan)

Các gate naturalness ≥4,2/5, preference ≥80%, emotion correctness ≥85% là đánh giá của con người — máy không tự chấm được. Quy định tối thiểu:

- **≥8 người nghe**, là người Việt bản ngữ, không thuộc nhóm phát triển, trải cả ba miền nếu được.
- Blind A/B: người nghe không biết mẫu nào của engine nào; thứ tự phát ngẫu nhiên.
- Mỗi người chấm toàn bộ 80 câu corpus; naturalness theo thang MOS 1–5.
- Kết quả lưu raw (từng người, từng câu) vào artifacts, không chỉ lưu trung bình.
- Chưa có panel ⇒ gate chủ quan ở trạng thái `BLOCKED`, không được suy diễn PASS từ cảm nhận nội bộ.

## 23.3 Agent eval

- intent;
- risk;
- tool;
- argument;
- confirmation;
- retry;
- result verification;
- source grounding;
- persona.

## 23.4 Soak

```text
30 phút
≥30 turn
≥10 barge-in
≥5 reconnect
≥3 LLM timeout
≥3 TTS failure
```

---

# 24. ACCEPTANCE CUỐI

Dự án chỉ đạt khi:

1. STT mặc định được chọn bằng benchmark.
2. TTS biểu cảm vượt gate chất lượng và latency.
3. Piper fallback hoạt động.
4. Persona tự nhiên và nhất quán.
5. Read-only tools có nguồn.
6. Action tools có confirmation.
7. Không false success.
8. Context bounded và summarized.
9. Tool/memory/session isolation pass.
10. Metrics giải thích toàn bộ turn.
11. Barge-in đạt target.
12. Repository reproducible.
13. Limitation còn lại được ghi trung thực.

---

# 25. QUYẾT ĐỊNH CUỐI

Đây là hướng duy nhất nên dùng cho dự án:

```text
Giữ Pipecat/FastAPI/SmallWebRTC
+
Nâng STT theo profile và benchmark
+
Một Agent Orchestrator
+
Pipecat Flows và typed tools
+
Knowledge có nguồn
+
Memory có kiểm soát
+
VieNeu expressive local
+
Piper fallback
+
Expression Composer
+
Confirmation, ACK, audit
```

Model thay đổi bằng profile; agent core không được phân mảnh theo từng model.
