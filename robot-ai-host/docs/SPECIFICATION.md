# Robot AI Host — Đặc tả hệ thống chi tiết

**Version:**0.1.0**Last updated:** 2026-07-31 **Status:**Development (PR-0 baseline locked, no E2E evidence)

**Source commit:**`ef1580b1da4f3d40a8fa2e77a6a6bad951e7994a`**Branch:**`session-upgrades`

---

## Mục lục

1. [Tổng quan dự án](#1-tổng-quan-dự-án)
2. [Kiến trúc hệ thống](#2-kiến-trúc-hệ-thống)
3. [Pipeline xử lý giọng nói](#3-pipeline-xử-lý-giọng-nói)
4. [API Reference](#4-api-reference)
5. [Quản lý phiên (Sessions)](#5-quản-lý-phiên-sessions)
6. [WebRTC & NAT Traversal](#6-webrtc--nat-traversal)
7. [Cấu hình (Config & Profiles)](#7-cấu-hình-config--profiles)
8. [Nhận dạng giọng nói (STT)](#8-nhận-dạng-giọng-nói-stt)
9. [Mô hình ngôn ngữ (LLM) & System Prompt](#9-mô-hình-ngôn-ngữ-llm--system-prompt)
10. [Tổng hợp giọng nói (TTS)](#10-tổng-hợp-giọng-nói-tts)
11. [Biểu cảm Robot & RTVI](#11-biểu-cảm-robot--rtvi)
12. [Knowledge Base & Grounding](#12-knowledge-base--grounding)
13. [Quản lý hội thoại (Context)](#13-quản-lý-hội-thoại-context)
14. [An toàn & Bảo mật](#14-an-toàn--bảo-mật)
15. [Admin Dashboard & API](#15-admin-dashboard--api)
16. [Triển khai & Vận hành](#16-triển-khai--vận-hành)
17. [Testing](#17-testing)
18. [Cấu trúc thư mục](#18-cấu-trúc-thư-mục)
19. [Biến môi trường (.env)](#19-biến-môi-trường-env)
20. [Các vấn đề đã biết & Hạn chế](#20-các-vấn-đề-đã-biết--hạn-chế)
21. [Lộ trình nâng cấp](#21-lộ-trình-nâng-cấp)

---

## 1. Tổng quan dự án

### 1.1 Mục tiêu

**Robot AI Host** là trợ lý giọng nói AI tiếng Việt dành cho môi trường trường học, chạy trên máy chủ cục bộ (MacBook Air M1), cho phép học sinh/giáo viên/phụ huynh tương tác bằng giọng nói qua WebRTC từ điện thoại hoặc trình duyệt.

### 1.2 Thông số kỹ thuật

| Thuộc tính | Giá trị |
|---|---|
| **Tên dự án** | `robot-ai-host` |
| **Phiên bản** | `0.1.0` |
| **Framework** | Pipecat v1.6.0 + FastAPI |
| **Python** | ≥3.11, <3.13 |
| **Build system** | Hatchling |
| **Transport** | WebRTC (SmallWebRTCTransport) |
| **Ngôn ngữ** | Tiếng Việt (vi-VN) |
| **TTS Engine** | VieNeu v3 Turbo (nội bộ, ONNX) |
| **STT Engine** Sherpa-onnxZipformer (nội bộ, INT8) Whisper local (hybrid profile) |
| **LLM Backend** | OpenAI-compatible API (Gemini 2.5 Flash Lite qua AGY endpoint) |
| **NAT Traversal** | Cloudflare TURN (per-session short-lived credentials) |
| **Tunnel** | Cloudflare Tunnel (trycloudflare.com quick tunnel) |
**Test count** 211 collected, 207 passed, 4 skipped (2026-07-31) |
| **Codebase** ~9,057 LOC Python (6,419 app + 2,638 tests) |

###1.2.1Model Manifest (PR-0 baseline)

| Model | Version/SHA | Backend |
|---|---|---|
| Pipecat | 1.6.0 | pip |
| Python | 3.12.12 | uv (cpython-3.12-macos-aarch64-none) |
| FastAPI | 0.139.2 | pip |
| ONNX Runtime | 1.24.4 | pip |
| PyJWT | 2.13.0 | pip |
| uvloop | 0.22.1 | pip |
| Sherpa-ONNX | 1.13.4 | pip (hybrid venv) |
| VieNeu | SDK | embedded |
| Whisper MLX | mlx-community/whisper-large-v3-turbo-q4 | MLX |
| Faster-Whisper | deepdml/faster-whisper-large-v3-turbo-ct2 | CTranslate2 |
| Piper voice | vi_VN-vais1000-medium | HTTP sidecar |
| macOS | 15.7.5 (Darwin 24.6.0 arm64) | M1 8GB 8-core |

Configuration SHA-256:`439af489acd0f6680f0b8eaf067b417acbfe3b529ca12492c39e0ba294e1bcee` (profiles.yaml + pyproject.toml + .env.example combined)

### 1.3 Người dùng mục tiêu

- **Học sinh**: tra cứu lịch học, hỏi đáp kiến thức, thủ tục trường
- **Giáo viên**: tra cứu thông tin, lịch công tác
- **Phụ huynh**: hỏi về thủ tục, biểu mẫu, liên hệ
- **Cán bộ nhà trường**: quản lý, cấu hình hệ thống qua dashboard

---

## 2. Kiến trúc hệ thống

### 2.1 Sơ đồ tổng quan

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INTERNET                                     │
│                                                                      │
│  Điện thoại / Browser (4G/WiFi)                                      │
│       │                                                              │
│       ├── HTTPS signaling ──► Cloudflare Tunnel ──► FastAPI :8000    │
│       │    (HTTP2, TLS)         (trycloudflare)      (localhost)     │
│       │                                                              │
│       └── WebRTC media ────► Cloudflare TURN ◄──── Pipecat Worker    │
│            (UDP/TCP/TLS)      (per-session cred)    (pipeline)       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Luồng kết nối chi tiết

#### Giai đoạn 1: Đăng ký thiết bị
```
Client                                    Server
  │                                         │
  ├─ POST /v1/devices/register ────────────►
  │  {provisioning_secret, device_id,      │
  │   device_type, firmware_version}        │
  │                                         ├─ Xác thực provisioning_secret
  │←─ {access_token, expires_in} ──────────┤
```

#### Giai đoạn 2: Tạo session
```
Client                                    Server
  │                                         │
  ├─ POST /v1/sessions ────────────────────►
  │  {profile, device_id, language,        │
  │   transport}                            │
  │  Authorization: Bearer {token}          │
  │                                         ├─ Kiểm tra giới hạn session
  │                                         ├─ Gọi Cloudflare TURN API
  │                                         │  POST /v1/turn/keys/{id}/credentials/generate
  │                                         │  → {username, credential, urls}
  │                                         ├─ Tạo session_id (UUID)
  │                                         ├─ Tạo JWT connection token
  │←─ {                                     │
  │     session_id,                         │
  │     webrtcUrl,                          │
  │     webrtc: {ice_servers, ...},         │  ← Pipecat server-side
  │     iceConfig: {iceServers: [...]},     │  ← Pipecat client-side KEY
  │     turnExpiresAt,                      │
  │     iceTransportPolicy: "all"           │
  │   } ───────────────────────────────────┤
```

#### Giai đoạn 3: WebRTC Negotiation
```
Client                                    Server
  │                                         │
  ├─ POST /v1/sessions/{id}/api/offer ─────►
  │  {sdp, type:"offer"}                    │
  │                                         ├─ Tạo SmallWebRTCConnection
  │                                         ├─ Tạo Pipeline (STT→LLM→TTS)
  │                                         ├─ Parse ICE servers cho server-side
  │←─ {sdp, type:"answer"} ────────────────┤
  │                                         │
  ├─ PATCH .../api/offer ──────────────────►
  │  {candidates: [{candidate,sdpMid,...}]} │
  │←─ 200 OK ──────────────────────────────┤
  │                                         │
  │═══════ WebRTC connected ═══════════════│
  │  audio hai chiều + data channel         │
  │                                         │
  │  ──► on_client_connected                │
  │       ├─ Gửi intro TTS (pre-rendered)   │
  │       ├─ Gửi robot behavior (greet)     │
  │       └─ Pipeline bắt đầu xử lý audio   │
```

### 2.3 Thành phần hệ thống

| Thành phần | Công nghệ | Vai trò |
|---|---|---|
| **API Server** | FastAPI + Uvicorn | REST API: đăng ký, session, SDP signaling |
| **Event Loop** | uvloop | High-performance async I/O |
| **WebRTC Transport** | Pipecat SmallWebRTCTransport | WebRTC media thời gian thực |
| **Cloudflare Tunnel** | cloudflared HTTP2 | Proxy HTTPS công khai (quick tunnel) |
| **Cloudflare TURN** | CF TURN API | Relay media khi direct connection thất bại |
| **STT** | Sherpa-onnx Zipformer | Nhận dạng tiếng Việt (WER 9.39%) |
| **LLM** | OpenAI-compatible (Gemini 2.5 Flash Lite) | Xử lý hội thoại, sinh phản hồi |
| **TTS** | VieNeu v3 Turbo (Two-Tier) | Tổng hợp giọng nói tiếng Việt |
| **VAD** | Silero VAD | Phát hiện giọng nói |
| **Auth** | PyJWT | Device registration + session tokens |

---

## 3. Pipeline xử lý giọng nói

### 3.1 Sơ đồ pipeline

```
transport.input()        ← Audio từ WebRTC
    │
    ▼
STT                      ← Nhận dạng giọng nói (Sherpa/Google/Mock)
    │
    ▼
STTGuard                 ← Lọc nhiễu, sửa lỗi chính tả (glossary)
    │
    ▼
WakeGate                 ← Gate idle/active cho không gian công cộng
    │
    ▼
UserAggregator           ← Gom câu hoàn chỉnh từ transcription
    │
    ▼
ContextCompactor         ← Nén context cũ (giữ 6-8 turn gần nhất)
    │
    ▼
TurnGrounding            ← Knowledge grounding + Safety check
    │
    ▼
SmallTalkBypass          ← Bỏ qua LLM cho chào hỏi đơn giản
    │
    ▼
LLM                      ← OpenAI-compatible streaming LLM
    │
    ▼
StreamDeduplicator       ← Lọc trùng lặp trong streaming output
    │
    ▼
ResponsePolicy           ← Hard cap sentences/words
    │
    ▼
TTS                      ← Two-tier TTS (VieNeu/Piper/Google/Mock)
    │
    ▼
transport.output()       ← Gửi audio về client
    │
    ▼
AssistantAggregator      ← Lưu response vào context
```

### 3.2 Chi tiết từng processor

#### 3.2.1 STT — Speech-to-Text
- **File:** `app/pipecat_runtime/sherpa_stt.py`
- **Provider:** `sherpa-onnx-zipformer-vi-int8-2025-04-20`
- **Decode time:** P50 0.088s (M1)
- **WER:** 9.39% (VIVOS benchmark)
- **Mode:** Offline (segment-level), không streaming
- **Input:** Audio PCM từ VAD-segmented buffer
- **Output:** `TranscriptionFrame`

#### 3.2.2 STTGuard
- **File:** `app/processors/stt_guard.py`
- **Chức năng:** Lọc nhiễu STT, sửa lỗi chính tả qua glossary
- **Glossary:** Từ `config/glossary.yaml` (tên riêng, thuật ngữ trường)
- **Bật/tắt:** `GLOSSARY_ENABLED` env var

#### 3.2.3 WakeGate
- **File:** `app/processors/wake_gate.py`
- **Chức năng:** Gate cho không gian công cộng
  - **Idle:** Không transcription nào đến LLM
  - **Active:** Kích hoạt qua RTVI `robot.wake` (button/screen touch)
  - **Timeout:** Tự động trở về idle sau `IDLE_TIMEOUT_SECONDS` (default 30s) không có user turn
- **Disabled mode:** Gate luôn active (dùng cho dev/browser)
- **Khi về idle:** Xóa transient visitor context

#### 3.2.4 UserAggregator
- **Framework:** Pipecat `LLMUserAggregatorParams`
- **VAD:** Silero VAD với params từ config
- **Aggregation:** Gom interim transcriptions thành câu hoàn chỉnh

#### 3.2.5 ContextCompactor
- **File:** `app/processors/context_compactor.py` + `app/core/context_manager.py`
- **Chức năng:** Giới hạn context window
  - Giữ `CONVERSATION_MAX_TURNS` (default 8) turn gần nhất
  - Các turn cũ hơn được tóm tắt
  - System prompt luôn được giữ nguyên

#### 3.2.6 TurnGrounding
- **File:** `app/processors/turn_grounding.py`
- **Chức năng kép:**
  1. **Knowledge Grounding:** Tìm thông tin trong `knowledge/school/` cho câu hỏi người dùng
     - Có hit → inject `[DỮ LIỆU NHÀ TRƯỜNG]` note vào context
     - Không hit + school topic → inject `"Mình chưa có thông tin đó"` để model từ chối
  2. **Safety Guard:** Phát hiện từ khóa nguy hiểm (self-harm, bullying, abuse)
     - Inject `[AN TOÀN]` response guideline
     - Ghi alert vào `artifacts/safety_alerts.jsonl`
- **Cleanup:** Note từ turn trước bị xóa trước khi thêm note mới

#### 3.2.7 SmallTalkBypass
- **File:** `app/processors/small_talk_bypass.py`
- **Chức năng:** Bỏ qua LLM cho các câu chào hỏi đơn giản
  - Chỉ trigger với utterance ≤ 6 từ
  - Pattern match: greeting, thanks, goodbye, name, how-are-you
  - **An toàn:** Không bypass nếu có school topic hoặc safety signal
- **Lợi ích:** 0ms LLM latency cho các câu ngắn

#### 3.2.8 LLM
- **File:** `app/pipecat_runtime/pipeline_factory.py` (`_create_openai_compatible_llm`)
- **Provider:** `OpenAILLMService` với endpoint tùy chỉnh
- **Streaming:** Có (default)
- **System prompt:** Build từ `config/assistant_school.yaml` + env vars
- **Params:** `temperature=0.5`, `max_tokens=100`, `timeout=30s`, retry on timeout

#### 3.2.9 StreamDeduplicator
- **File:** `app/processors/stream_deduplicator.py`
- **Chức năng:** Lọc các TextFrame trùng lặp từ streaming LLM output
  - Một số LLM gửi duplicate text deltas trong streaming

#### 3.2.10 ResponsePolicy
- **File:** `app/processors/response_policy.py`
- **Chức năng:** Hard ceiling cho response
  - `RESPONSE_MAX_SENTENCES` (default 5)
  - `RESPONSE_MAX_WORDS` (default 100)
- **Cơ chế:** Đếm cumulative từ lúc `LLMFullResponseStartFrame`, swallow sau khi hết budget
- **Note:** Đây là overflow guard; everyday brevity do system prompt điều khiển

#### 3.2.11 TTS — Two-Tier TTS
- **File:** `app/pipecat_runtime/two_tier_tts.py`
- **Architecture:**
  - **Opener:** Câu đầu tiên — ưu tiên chất lượng/expressiveness cao
  - **Expressive:** Các câu còn lại — streaming hoặc batch
- **VieNeu v3 Turbo:**
  - **Model:** ONNX, 48kHz PCM s16le
  - **Styles:** `tu_nhien`, `tin_tuc`, `doc_truyen`
  - **Voices:** Đoan Trang, Anh Thư, Thanh Hà, Minh Quân, Ngọc Lan, Hoàng Nam
  - **Streaming:** Có (optional, `VIENEU_STREAMING`)
  - **Warm-up:** Chạy background task trước session đầu tiên
- **Piper HTTP fallback:** Khi VieNeu không khả dụng

---

## 4. API Reference

### 4.1 Endpoints

| Method | Endpoint | Auth | Mô tả |
|---|---|---|---|
| `POST` | `/v1/devices/register` | provisioning_secret | Đăng ký thiết bị mới |
| `POST` | `/v1/sessions` | Bearer token | Tạo WebRTC session |
| `POST` | `/v1/sessions/{id}/api/offer` | connection token | Gửi SDP offer |
| `PATCH` | `/v1/sessions/{id}/api/offer` | connection token | Gửi ICE candidates |
| `POST` | `/v1/sessions/{id}/heartbeat` | connection token | Heartbeat giữ session |
| `DELETE` | `/v1/sessions/{id}` | Bearer token | Đóng session |
| `GET` | `/health` | none | Health check |
| `GET` | `/v1/admin/settings` | Bearer token | Đọc tất cả settings |
| `PUT` | `/v1/admin/settings` | Bearer token | Cập nhật settings |
| `GET` | `/v1/admin/voices` | Bearer token | Danh sách voice TTS |
| `GET` | `/v1/admin/knowledge` | Bearer token | Liệt kê knowledge files |
| `POST` | `/v1/admin/knowledge/upload` | Bearer token | Upload knowledge file |
| `DELETE` | `/v1/admin/knowledge/{name}` | Bearer token | Xóa knowledge file |
| `POST` | `/v1/admin/restart` | Bearer token | Restart server |

### 4.2 Static Routes

| Path | Content | Mô tả |
|---|---|---|
| `/client/` | `clients/browser/dashboard.html` | Admin dashboard quản lý |
| `/client/chat` | `clients/browser/index.html` | Voice client (test micro) |
| `/robot/` | `clients/desktop_robot_emulator/index.html` | Robot face emulator |

### 4.3 Authentication Flow

1. **Device Registration:** `provisioning_secret` → `access_token` (JWT, hết hạn sau `JWT_EXPIRY_SECONDS`)
2. **Session Creation:** `access_token` → validate device → tạo session
3. **WebRTC Negotiation:** `connection_token` (JWT, scope: session) → validate session ownership

### 4.4 Request/Response Models

#### POST /v1/devices/register
```json
// Request
{
  "device_id": "phone-001",
  "device_type": "mobile_browser",
  "firmware_version": "0.1.0",
  "provisioning_secret": "dev-provisioning-secret",
  "capabilities": {"audio": true, "video": false}
}
// Response
{
  "device_id": "phone-001",
  "access_token": "eyJ...",
  "expires_in": 3600,
  "heartbeat_interval_seconds": 15
}
```

#### POST /v1/sessions
```json
// Request
{
  "device_id": "phone-001",
  "profile": "hybrid_local_vi",
  "language": "vi-VN",
  "transport": "webrtc"
}
// Response
{
  "session_id": "sess_abc123...",
  "status": "created",
  "expires_in": 3600,
  "webrtcUrl": "wss://...",
  "webrtc": {"ice_servers": [...], "connection_token": "..."},
  "turnExpiresAt": 1751234567.0,
  "iceTransportPolicy": "all",
  "iceConfig": {
    "iceServers": [
      {"urls": "stun:stun.cloudflare.com:3478"},
      {
        "urls": [
          "turn:turn.cloudflare.com:3478?transport=udp",
          "turn:turn.cloudflare.com:3478?transport=tcp",
          "turn:turn.cloudflare.com:80?transport=tcp",
          "turns:turn.cloudflare.com:5349?transport=tcp",
          "turns:turn.cloudflare.com:443?transport=tcp"
        ],
        "username": "per-session-username",
        "credential": "per-session-credential"
      }
    ]
  }
}
```

---

## 5. Quản lý phiên (Sessions)

### 5.1 Session Lifecycle

```
CREATED ──► ACTIVE ──► CLOSING ──► CLOSED
   │                       │
   └───────────────────────┘
              │
           ERROR (giữ lại evidence để debug)
```

### 5.2 Session States

| State | Mô tả |
|---|---|
| `CREATED` | Session đã tạo, chưa có WebRTC connection |
| `ACTIVE` | WebRTC đã connected, pipeline đang chạy |
| `CLOSING` | Đang cleanup worker và resources |
| `CLOSED` | Đã cleanup xong |
| `ERROR` | Lỗi — giữ lại để debug |

### 5.3 Giới hạn session

- **Global:** `MAX_SESSIONS` (default 4) — tổng số session active đồng thời
- **Per-profile:** `LOCAL_STT_MAX_SESSIONS` (default 4) — giới hạn riêng cho `hybrid_local_vi`
- **Heartbeat timeout:** `HEARTBEAT_TIMEOUT_SECONDS` (default 30s) — auto-cleanup khi client mất kết nối
- **Cleanup loop:** Chạy định kỳ (background task), quét expired sessions

### 5.4 Worker Lifecycle

1. `create_worker_for_session()` — Tạo PipelineWorker + WorkerRunner + PipelineBundle
2. `register_worker()` — Đăng ký vào SessionManager (chỉ 1 worker/session)
3. `activate_session()` — CREATED → ACTIVE
4. `_run_worker_runner()` — Chạy runner trong background task
5. Khi disconnect:
   - `on_client_disconnected` → `runner.cancel()` → cleanup
   - `aclose()` → đóng HTTP sessions, release resources

---

## 6. WebRTC & NAT Traversal

### 6.1 ICE Candidate Selection

```
1. Host candidates (IP local)     → ưu tiên cao nhất
2. srflx candidates (STUN)        → nếu NAT cho phép
3. Relay candidates (TURN)        → nếu direct thất bại
   ├── TURN UDP :3478             → nhanh nhất
   ├── TURN TCP :3478             → fallback
   ├── TURN TCP :80               → bypass firewall
   ├── TURN TLS :5349             → secure relay
   └── TURN TLS :443              → LUÔN hoạt động (không bị chặn)
```

### 6.2 Cloudflare TURN Integration

- **File:** `app/pipecat_runtime/turn_credentials.py`
- **API:** `POST https://rtc.live.cloudflare.com/v1/turn/keys/{KEY_ID}/credentials/generate`
- **Credential:** Per-session, short-lived (TTL từ `CLOUDFLARE_TURN_TTL_SECONDS`, default 3600s)
- **Fallback:** Nếu CF TURN không được cấu hình → dùng static `WEBRTC_ICE_SERVERS`

### 6.3 ICE Config (Critical Fix)

**Vấn đề:** Pipecat server-side gửi ICE servers trong `webrtc.ice_servers`, nhưng Pipecat client-js đọc `iceConfig.iceServers` ở top-level.

**Fix:** `app/main.py` trả về **cả hai** field:
- `webrtc.ice_servers` — cho server-side Pipecat transport
- `iceConfig.iceServers` — cho client-side Pipecat SDK
- ICE servers cũng được pass vào server-side transport qua `SmallWebRTCRequest.ice_servers`

### 6.4 Transport Toggles

| Env Var | Default | Mô tả |
|---|---|---|
| `WEBRTC_ENABLE_STUN` | true | Bật STUN |
| `WEBRTC_ENABLE_TURN_UDP` | true | TURN qua UDP |
| `WEBRTC_ENABLE_TURN_TCP` | true | TURN qua TCP |
| `WEBRTC_ENABLE_TURN_TLS` | true | TURN qua TLS |
| `WEBRTC_ICE_POLICY` | "all" | all \| relay |
| `WEBRTC_FORCE_RELAY` | false | Chỉ dùng TURN (testing) |

### 6.5 Cloudflare Tunnel

- **Tool:** `cloudflared tunnel --url https://localhost:8000 --no-tls-verify --protocol http2`
- **Type:** Quick tunnel (URL thay đổi mỗi lần)
- **Auto-restart:** `start.sh` retry 3 lần khi khởi động, auto-restart khi tunnel rớt
- **Named tunnel:** Có config `cloudflared-config.yml` nhưng chưa triển khai production

---

## 7. Cấu hình (Config & Profiles)

### 7.1 Hệ thống config

```
config/
├── profiles.yaml           ← Runtime profiles (mock, google_vi, hybrid_local_vi)
├── assistant_school.yaml   ← Persona & behavior
├── glossary.yaml           ← Từ điển sửa lỗi STT
└── stt_candidates.yaml     ← Cấu hình STT candidates

.env                        ← Tất cả biến môi trường
```

### 7.2 Runtime Profiles

#### mock
- **STT:** Scripted transcripts (deterministic)
- **LLM:** MockLLMService (phản hồi cứng)
- **TTS:** MockTTSService (silence)
- **Dùng cho:** Unit tests, integration tests

#### google_vi
- **STT:** Google Cloud Speech-to-Text (streaming)
- **LLM:** OpenAI-compatible (Gemini)
- **TTS:** Google Cloud Text-to-Speech (Chirp3-HD hoặc Journey)
- **Yêu cầu:** `GOOGLE_APPLICATION_CREDENTIALS`

#### hybrid_local_vi (Production default)
- **STT:** Sherpa-onnx Zipformer (local, INT8)
- **LLM:** OpenAI-compatible (Gemini qua AGY endpoint)
- **TTS:** VieNeu v3 Turbo (local, ONNX) + Piper HTTP fallback
- **Đặc điểm:** Không phụ thuộc Google Cloud, chạy hoàn toàn offline cho voice

### 7.3 Assistant Persona

- **File:** `config/assistant_school.yaml`
- **Tên:** "Mây Mây" (override qua `PERSONA_NAME` env)
- **Xưng hô:** "mình – bạn"
- **Tính cách:** ấm áp, điềm tĩnh, chủ động
- **Cấm:** giả người, nhận thuộc Google/DeepMind/OpenAI, bịa dữ liệu trường

### 7.4 Settings Flow

```
.env ──► Settings (Pydantic BaseSettings)
            │
            ├──► validate_profile_runtime() — fail fast trước WebRTC
            │
            └──► Admin API (GET/PUT /v1/admin/settings) — đọc/ghi .env
```

---

## 8. Nhận dạng giọng nói (STT)

### 8.1 Sherpa-onnx Zipformer

- **File:** `app/pipecat_runtime/sherpa_stt.py`
- **Model:** `csukuangfj/sherpa-onnx-zipformer-vi-int8-2025-04-20`
- **Loại:** Offline recognizer (non-streaming)
- **Decode time:** ~0.1s per segment (đủ nhanh cho voice conversation)
- **Sample rate:** Pipeline native (sherpa tự resample qua feature extractor)
- **Download:** Tự động từ HuggingFace Hub khi khởi động

### 8.2 Google Cloud STT

- **Provider:** `google` trong profile
- **Model:** Chirp (configurable qua `GOOGLE_STT_MODEL`)
- **Mode:** Streaming recognition
- **Yêu cầu:** `GOOGLE_APPLICATION_CREDENTIALS` file

### 8.3 Mock STT

- **File:** `app/pipecat_runtime/providers.py`
- **Scripted:** `MOCK_SCRIPTED_TRANSCRIPTS` (pipe-separated)
- **Dùng cho:** Tests

---

## 9. Mô hình ngôn ngữ (LLM) & System Prompt

### 9.1 LLM Service

- **Provider:** `OpenAILLMService` (OpenAI-compatible API)
- **Model:** `LLM_MODEL` env (default: `agy/gemini-2.5-flash-lite`)
- **Base URL:** `LLM_BASE_URL` env (AGY endpoint on :20128)
- **API Key:** `LLM_API_KEY` env
- **Params:**
  - `LLM_TEMPERATURE`: 0.5 (conversation), 0.45–0.6 range
  - `LLM_MAX_TOKENS`: 100
  - `LLM_TIMEOUT_SECONDS`: 30
  - `LLM_RETRY_ON_TIMEOUT`: true

### 9.2 System Prompt

- **File:** `app/core/system_prompt.py`
- **Source:** `config/assistant_school.yaml` → `build_system_prompt()`
- **Budget:** 500-800 tokens (spec 9.7)
- **Cấu trúc:**
  1. Identity: "Bạn là {name}, trợ lý AI của trường"
  2. Cách trả lời: ngắn gọn, tự nhiên, không hành chính
  3. Độ dài: chào 1 câu, trò chuyện 1-2 câu, tra cứu 1-3 câu
  4. Giọng nói: trẻ trung, ngọt ngào, thán từ "Dạ/À/nè/nha"
  5. Robot face: đồng ý làm biểu cảm, không từ chối
  6. An toàn: không giả người, không bịa, không tiết lộ model

### 9.3 Small Talk Bypass

- **Pattern matching** (≤6 từ):
  - Greeting: "xin chào", "chào", "hi", "hello"
  - Thanks: "cảm ơn", "cám ơn", "thanks"
  - Goodbye: "tạm biệt", "bye", "bai bai"
  - Name: "bạn tên gì", "mày tên gì"
  - How are you: "khỏe không", "thế nào"
- **Safety guard:** Không bypass nếu có school topic hoặc safety keyword

---

## 10. Tổng hợp giọng nói (TTS)

### 10.1 VieNeu v3 Turbo (Two-Tier)

- **File:** `app/pipecat_runtime/vieneu_engine.py` + `app/pipecat_runtime/two_tier_tts.py`
- **Model:** ONNX, CPU inference, 48kHz PCM s16le
- **Voices:** 6 giọng (Đoan Trang, Anh Thư, Thanh Hà, Minh Quân, Ngọc Lan, Hoàng Nam)
  - Default: `VIENEU_VOICE` env → "Đoan Trang"
- **Styles:** `tu_nhien`, `tin_tuc`, `doc_truyen`
  - Expression mapping:
    - neutral/friendly/calm → `tu_nhien`
    - cheerful/empathetic/encouraging → `doc_truyen`
    - serious → `tin_tuc`
- **Streaming:** Optional, `VIENEU_STREAMING` env
  - ON: streaming từng chunk (lower TTFB)
  - OFF: batch toàn bộ câu
- **Speed:** `VIENEU_SPEED` (1.0 default)
- **Temperature:** `VIENEU_TEMPERATURE` (0.7 default)
- **Style:** `VIENEU_STYLE` ("friendly" default)

### 10.2 Two-Tier Architecture

| Tier | Mô tả | Trigger |
|---|---|---|
| **Opener** | Câu đầu tiên, chất lượng cao | Luôn chạy cho câu đầu |
| **Expressive** | Các câu còn lại | Streaming hoặc batch |
| **Fallback** | Piper HTTP | Khi VieNeu không khả dụng |

### 10.3 Intro (Cached)

- **Intro text:** `"Mình là {PERSONA_NAME}, mình có thể giúp gì cho bạn nè?"`
- **Caching:** Pre-rendered, gửi ngay khi client connected
- **Retry:** Đợi VieNeu warm-up (lên đến 16 lần × 0.5s = 8s max)
- **Context:** Intro được thêm vào context history

### 10.4 Warm-up Strategy

1. `VieNeuEngine()` được tạo khi pipeline khởi tạo
2. `start_warm_up()` chạy background task → load model ONNX (~tens of seconds)
3. Khi client connect, `worker_factory.py` đợi `engine.ready` (max 8s)
4. Nếu chưa ready → intro bị skip (không crash)

### 10.5 Google TTS (google_vi profile)

- **Voice:** `GOOGLE_TTS_VOICE` (phải bắt đầu `vi-VN-`)
- **Model:** Chirp3-HD hoặc Journey (streaming)
- **Yêu cầu:** Google Cloud credentials

### 10.6 Piper HTTP (fallback)

- **Mode:** Sentence-level aggregation
- **Voice:** `vi_VN-vais1000-medium`
- **Endpoint:** `PIPER_BASE_URL`

---

## 11. Biểu cảm Robot & RTVI

### 11.1 Robot Face Emulator

- **Path:** `/robot/` → `clients/desktop_robot_emulator/index.html`
- **Features:**
  - Mascot "Mây Mây" — mắt, miệng, lông mày, biểu cảm
  - Auto-connect (không cần UI)
  - Hidden controls (minimal)
  - CSS animations cho các emotion states
  - Aura effect

### 11.2 RTVI Custom Messages

- **File:** `app/pipecat_runtime/rtvi.py`
- **Robot behaviors:** Gửi qua RTVI data channel
  - `robot.behavior`: Lệnh biểu cảm (greet, emotion, intensity, duration)
  - `robot.behavior.ack`: Client xác nhận đã thực hiện
- **Client messages:**
  - `client.playback.started/stopped`: Audio playback status
  - `client.barge_in.stopped`: Barge-in hoàn tất
  - `client.webrtc.connected`: WebRTC connection metrics
  - `client.audio.received`: Audio received confirmation
  - `robot.wake/sleep`: Kích hoạt/idle gate
  - `robot.capabilities`, `robot.mute/unmute`: Robot control
  - `conversation.reset`: Reset context

### 11.3 Behavior Validation

- **File:** `app/robot/validator.py`
- Validate behavior name, emotion, intensity (0.0-1.0), duration
- Reject nếu invalid → log warning, không gửi

### 11.4 Metrics từ Robot

- `METRIC_BEHAVIOR_ACK`: Thời gian từ lúc gửi behavior đến khi client ACK
- `METRIC_CLIENT_AUDIBLE_START`: Thời gian đến khi client bắt đầu phát audio
- `METRIC_BARGE_IN_STOP`: Thời gian xử lý barge-in
- `METRIC_WEBRTC_CONNECT`: Thời gian thiết lập WebRTC connection

---

## 12. Knowledge Base & Grounding

### 12.1 Knowledge Store

- **Directory:** `knowledge/school/`
- **Format:** YAML files
- **Files:**
  - `general_info.yaml` — Thông tin chung về trường
  - `contacts.yaml` — Danh bạ
  - `schedules_deadlines.yaml` — Lịch học, deadline
  - `forms.yaml` — Biểu mẫu, thủ tục
- **Search:** In-memory matching qua `KnowledgeStore` class

### 12.2 Grounding Flow

1. Mỗi user turn → `TurnGroundingProcessor` search knowledge
2. Nếu tìm thấy → inject `[DỮ LIỆU NHÀ TRƯỜNG]` system note với source metadata
3. Nếu school topic nhưng không có data → inject explicit "no data" note
4. Model phải: dùng data nếu có, từ chối nếu không có
5. Notes từ turn trước được remove trước khi thêm mới

### 12.3 Knowledge Upload (Admin)

- **API:** `POST /v1/admin/knowledge/upload`
- **Giới hạn:** 10MB, chỉ `.yaml`, `.yml`, `.txt`, `.md`
- **Quản lý:** List/Delete qua dashboard

---

## 13. Quản lý hội thoại (Context)

### 13.1 Context Window

- `CONVERSATION_MAX_TURNS`: 8 turns (default)
- 6-8 turns gần nhất được giữ verbatim
- Các turn cũ hơn → summarized (qua `ContextCompactor`)
- System prompt luôn ở đầu context

### 13.2 Context Reset

- **Trigger:** RTVI message `conversation.reset`
- **Hành vi:** Xóa tất cả history, giữ system prompt
- `PipelineBundle.reset_conversation()` → `ContextManager.reset()`

### 13.3 Idle Context Clear

- Khi WakeGate về idle → xóa transient visitor context
- Giữ permanent context (system prompt, school data)

---

## 14. An toàn & Bảo mật

### 14.1 Safety Guard (TurnGrounding)

- **Patterns:** self-harm, bullying, abuse, self-destructive behavior
- **Action:**
  1. Inject `[AN TOÀN]` guideline vào context
  2. Ghi alert vào `artifacts/safety_alerts.jsonl` (local only)
  3. Model trả lời theo guideline an toàn
- **Không gửi đi đâu** tự động

### 14.2 Authentication

- **Device registration:** `provisioning_secret` → JWT access_token
- **Session:** JWT connection_token (scoped to session_id)
- **Admin API:** Bearer token từ device registration
- **JWT expiry:** `JWT_EXPIRY_SECONDS` (default 3600s)

### 14.3 Data Security

- Tất cả xử lý local, không gửi dữ liệu ra ngoài (trừ LLM API)
- Safety alerts lưu local file JSONL
- Metrics lưu local file JSONL
- Session data in-memory only

### 14.4 HTTPS

- **LAN:** Self-signed certificate (`certs/dev-cert.pem`, `certs/dev-key.pem`)
- **WAN:** Cloudflare Tunnel tự động cung cấp TLS
- **Certificate generation:** `scripts/gen_self_signed_cert.sh`

---

## 15. Admin Dashboard & API

### 15.1 Dashboard

- **Path:** `/client/` → `clients/browser/dashboard.html`
- **Tabs:**
  - **Voice (TTS):** Chọn voice, speed, style, temperature
  - **Model (LLM):** Model, API key, base URL, temperature, max tokens
  - **Speech (STT):** STT candidate, language
  - **Knowledge:** Upload, list, delete files
  - **System:** Max sessions, heartbeat timeout, restart

### 15.2 Editable Settings (Whitelist)

| Group | Keys |
|---|---|
| **TTS** | `VIENEU_VOICE`, `VIENEU_SPEED`, `VIENEU_STYLE`, `VIENEU_TEMPERATURE` |
| **LLM** | `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS` |
| **STT** | `STT_CANDIDATE` |
| **SYSTEM** | `MAX_SESSIONS`, `LOCAL_STT_MAX_SESSIONS`, `HEARTBEAT_TIMEOUT_SECONDS` |

### 15.3 Settings Update Flow

1. Admin gửi `PUT /v1/admin/settings` với group + key → value
2. Server validate key trong whitelist
3. Ghi vào `.env` (preserve comments + order)
4. Yêu cầu restart để apply

---

## 16. Triển khai & Vận hành

### 16.1 Khởi động

```bash
cd robot-ai-host
./start.sh
```

**start.sh workflow:**
1. Kill old server process (port 8000)
2. Start server: `PYTHONPATH=. .venv-hybrid/bin/python -m app.main --profile hybrid_local_vi`
3. Health check HTTPS `localhost:8000/health` (max 20 lần × 1s)
4. Start Cloudflare tunnel với HTTP2 protocol
5. Parse tunnel URL từ log
6. Retry tunnel 3 lần nếu fail
7. Monitor loop: auto-restart tunnel khi rớt

### 16.2 Dừng

```bash
Ctrl+C  # start.sh trap cleanup → kill server + tunnel
```

### 16.3 Health Check

```bash
# Local
curl -sk https://127.0.0.1:8000/health

# Public
curl -sk https://<tunnel-url>/health
```

### 16.4 Log Monitoring

```bash
# Các log quan trọng:
turn_credential_generated    # ✅ TURN credential OK
vieneu_loaded                # ✅ TTS model loaded
client_connected             # ✅ WebRTC connected
session_heartbeat_expired    # ❌ Client mất kết nối
max_sessions_reached         # ❌ Quá giới hạn session
turn_credential_failed       # ❌ TURN API fail
```

### 16.5 Environment

- **Virtualenv:** `.venv-hybrid` (Python 3.12)
- **PYTHONPATH:** `.` (CRITICAL — project root phải trong path)
- **Lưu ý:** Hermes PYTHONPATH conflict → luôn `PYTHONPATH=` trước lệnh Python trong project venv

---

## 17. Testing

### 17.1 Test Structure

```
tests/
├── conftest.py                       # Pytest fixtures
├── unit/                             # 20+ unit test files
│   ├── test_config.py               # Settings validation
│   ├── test_sessions.py             # Session manager
│   ├── test_pipeline_factory.py     # Pipeline creation (?)
│   ├── test_worker_factory.py       # Worker creation
│   ├── test_system_prompt.py        # System prompt builder
│   ├── test_wake_gate.py            # Wake/idle gate
│   ├── test_small_talk_bypass.py    # Small-talk bypass
│   ├── test_turn_grounding.py       # Grounding + safety
│   ├── test_response_policy.py      # Response limits
│   ├── test_sherpa_stt.py           # STT service
│   ├── test_two_tier_tts.py         # TTS service
│   ├── test_two_tier_resample.py    # TTS resampling
│   ├── test_text_sanitizer.py       # Text sanitization
│   ├── test_metrics.py              # Latency metrics
│   ├── test_routing.py              # Routing logic
│   ├── test_fake_adapter.py         # Robot fake adapter
│   ├── test_robot_messages.py       # Robot messages
│   ├── test_behavior_validator.py   # Behavior validation
│   ├── test_expression.py           # Expression composer
│   ├── test_glossary.py             # Glossary corrector
│   ├── test_context_manager.py      # Context management
│   ├── test_memory.py              # User memory
│   ├── test_personal_tools.py       # Personal tools
│   ├── test_knowledge_tools.py      # Knowledge tools
│   ├── test_tool_gateway.py         # Tool gateway
│   ├── test_hybrid_source_contract.py # Hybrid source
│   └── test_glm_local_preset.py     # GLM preset
├── integration/
│   └── test_api.py                  # API integration tests
├── e2e/                             # TRỐNG — chưa có E2E tests
└── manual/
    └── test_voice_evidence.py       # Manual voice test
```

### 17.2 Test Stats

- **Tổng tests:** 211 collected, 207 passed, 4 skipped (2026-07-31)
- **Status:** 207 PASS, 4 SKIP (evidence flag absent: 2, zipformer model not cached: 2)
- **Coverage:** ~29.1% (2,638/9,057 LOC)
- **Framework:** pytest + pytest-asyncio
- **Asyncio mode:** auto

### 17.3 Running Tests

```bash
cd robot-ai-host
PYTHONPATH=. .venv-hybrid/bin/pytest tests/ -v
```

### 17.4 Missing Tests

| Module | Priority |
|---|---|
| `admin.py` | Medium |
| `turn_credentials.py` | Low (cần API key) |
| E2E WebRTC test | **High** |
| E2E ICE negotiation | **High** |
| Load/stress test | Low |

---

## 18. Cấu trúc thư mục

```
robot-ai-host/
├── app/                              ← Mã nguồn chính
│   ├── __init__.py
│   ├── main.py                      ← FastAPI server, API endpoints (869 lines)
│   ├── config.py                    ← Settings, profiles, validation (425 lines)
│   ├── sessions.py                  ← Session manager (284 lines)
│   ├── admin.py                     ← Admin API (224 lines)
│   ├── auth.py                      ← JWT authentication
│   ├── logging_utils.py             ← Structured logging (structlog)
│   │
│   ├── core/                        ← Business logic
│   │   ├── system_prompt.py         ← Build system prompt from YAML
│   │   ├── knowledge.py            ← Knowledge store
│   │   ├── memory.py               ← User memory
│   │   ├── context_manager.py       ← Conversation context management
│   │   ├── task_state.py            ← Task state management
│   │   ├── expression.py            ← Expression composer
│   │   ├── glossary.py             ← Glossary corrector
│   │   ├── routing.py              ← Routing logic
│   │   └── device_manager.py        ← Device management
│   │
│   ├── pipecat_runtime/             ← Pipecat services & utilities
│   │   ├── worker_factory.py        ← Worker + runner creation
│   │   ├── pipeline_factory.py      ← Pipeline creation (mock/google/hybrid)
│   │   ├── turn_credentials.py      ← Cloudflare TURN service
│   │   ├── vieneu_engine.py         ← VieNeu TTS engine adapter
│   │   ├── sherpa_stt.py            ← Sherpa STT service
│   │   ├── two_tier_tts.py          ← Two-tier TTS service
│   │   ├── providers.py             ← Mock providers (test)
│   │   ├── rtvi.py                  ← RTVI custom messaging
│   │   ├── metrics.py               ← Latency tracker
│   │   ├── observers.py             ← Runtime observers
│   │   ├── ice_utils.py             ← ICE server parsing
│   │   ├── text_sanitizer.py        ← Text sanitization
│   │   ├── text_filter.py           ← Vietnamese speech text filter
│   │   └── intro_cache.py           ← Cached intro TTS
│   │
│   ├── processors/                  ← Pipeline processors
│   │   ├── stt_guard.py             ← STT output guard
│   │   ├── wake_gate.py             ← Idle/active gate
│   │   ├── context_compactor.py     ← Context compaction
│   │   ├── turn_grounding.py        ← Knowledge grounding + safety
│   │   ├── small_talk_bypass.py     ← Heuristic small-talk bypass
│   │   ├── stream_deduplicator.py   ← LLM stream dedup
│   │   └── response_policy.py       ← Hard sentence/word limits
│   │
│   ├── tools/                       ← Tool gateway + tools
│   │   ├── gateway.py               ← Typed tool gateway
│   │   ├── personal_tools.py        ← Personal tools
│   │   └── school_tools.py          ← School-related tools
│   │
│   └── robot/                       ← Robot interface
│       ├── messages.py              ← Behavior message models
│       ├── validator.py             ← Behavior validation
│       └── fake_adapter.py          ← Fake robot adapter (testing)
│
├── config/                           ← Configuration files
│   ├── profiles.yaml                ← Runtime profiles
│   ├── assistant_school.yaml        ← Persona definition
│   ├── glossary.yaml                ← STT correction glossary
│   └── stt_candidates.yaml          ← STT candidate configs
│
├── knowledge/                        ← Knowledge base
│   └── school/
│       ├── general_info.yaml
│       ├── contacts.yaml
│       ├── schedules_deadlines.yaml
│       └── forms.yaml
│
├── clients/                          ← Frontend clients
│   ├── browser/
│   │   ├── dashboard.html            ← Admin dashboard
│   │   └── index.html                ← Voice client
│   └── desktop_robot_emulator/
│       ├── index.html                ← Robot face emulator
│       └── node_modules/             ← (Vite + Pipecat SDK)
│
├── tests/                            ← Test suite
│   ├── conftest.py
│   ├── unit/                         ← 20+ unit test files
│   ├── integration/
│   │   └── test_api.py
│   ├── e2e/                          ← TRỐNG
│   └── manual/
│       └── test_voice_evidence.py
│
├── scripts/                          ← Utility scripts
│   ├── configure_glm_local.py
│   ├── verify_upstream_source.py
│   ├── check_cloud_profile.py
│   ├── check_hybrid_profile.py
│   ├── check_llm_endpoint.py
│   ├── check_acceleration.py
│   ├── load_test.py
│   ├── verify_deps.py
│   ├── report_latency.py
│   └── soak_stream_tts.py
│
├── benchmarks/                       ← Performance benchmarks
│   ├── stt/
│   │   └── run_benchmark.py
│   └── tts/
│       └── vieneu_smoke.py
│
├── certs/                            ← SSL certificates
│   ├── dev-cert.pem
│   └── dev-key.pem
│
├── artifacts/                        ← Runtime artifacts
│   ├── upgrade/
│   │   └── voice_samples/
│   ├── metrics.jsonl                 ← Latency metrics
│   └── safety_alerts.jsonl           ← Safety alerts
│
├── docs/                             ← Documentation
│   ├── SPECIFICATION.md              ← ← ← FILE NÀY
│   ├── ARCHITECTURE.md
│   ├── TROUBLESHOOTING.md
│   ├── VERIFICATION_REPORT.md
│   ├── PROJECT_EVALUATION.md
│   ├── DASHBOARD_PLAN.md
│   ├── CODE_REVIEW.md
│   └── CODE_REVIEW_ROUND2.md
│
├── .env                              ← Environment variables
├── .env.example                      ← (nên tạo)
├── .gitignore
├── pyproject.toml                    ← Project metadata + dependencies
├── cloudflared-config.yml            ← Named tunnel config
├── start.sh                          ← Startup script
└── reports/                          ← (có thể merge vào docs/)
```

---

## 19. Biến môi trường (.env)

### 19.1 Server Core

| Variable | Default | Mô tả |
|---|---|---|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `SSL_CERTFILE` | `""` | Path to SSL certificate |
| `SSL_KEYFILE` | `""` | Path to SSL key |
| `MAX_SESSIONS` | `4` | Max concurrent sessions |
| `LOCAL_STT_MAX_SESSIONS` | `4` | Max concurrent local STT sessions |
| `HEARTBEAT_TIMEOUT_SECONDS` | `30` | Session heartbeat timeout |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DEFAULT_PROFILE` | `mock` | Default runtime profile |

### 19.2 Authentication

| Variable | Default | Mô tả |
|---|---|---|
| `PROVISIONING_SECRET` | `change-me-in-production` | Device registration secret |
| `JWT_SECRET_KEY` | `change-me-in-production` | JWT signing key |
| `JWT_EXPIRY_SECONDS` | `3600` | Token expiry (1 hour) |

### 19.3 WebRTC & ICE

| Variable | Default | Mô tả |
|---|---|---|
| `WEBRTC_ICE_SERVERS` | Google STUN | Static ICE servers (fallback) |
| `WEBRTC_ENABLE_STUN` | `true` | Enable STUN |
| `WEBRTC_ENABLE_TURN_UDP` | `true` | Enable TURN UDP |
| `WEBRTC_ENABLE_TURN_TCP` | `true` | Enable TURN TCP |
| `WEBRTC_ENABLE_TURN_TLS` | `true` | Enable TURN TLS |
| `WEBRTC_ICE_POLICY` | `all` | ICE policy (all \| relay) |
| `WEBRTC_FORCE_RELAY` | `false` | Force TURN only |

### 19.4 Cloudflare TURN

| Variable | Default | Mô tả |
|---|---|---|
| `CLOUDFLARE_TURN_KEY_ID` | `""` | CF TURN key ID |
| `CLOUDFLARE_TURN_API_TOKEN` | `""` | CF TURN API token |
| `CLOUDFLARE_TURN_TTL_SECONDS` | `3600` | TURN credential TTL |

### 19.5 LLM

| Variable | Default | Mô tả |
|---|---|---|
| `LLM_API_KEY` | `""` | LLM API key |
| `LLM_BASE_URL` | `""` | LLM endpoint base URL |
| `LLM_MODEL` | `""` | LLM model name |
| `LLM_TEMPERATURE` | `0.5` | Generation temperature |
| `LLM_MAX_TOKENS` | `100` | Max output tokens |
| `LLM_STREAM` | `true` | Enable streaming |
| `LLM_TIMEOUT_SECONDS` | `30` | Request timeout |
| `LLM_RETRY_ON_TIMEOUT` | `true` | Retry on timeout |
| `LLM_DEFAULT_HEADERS_JSON` | `{}` | Custom headers |

### 19.6 TTS (VieNeu)

| Variable | Default | Mô tả |
|---|---|---|
| `VIENEU_VOICE` | `"Đoan Trang"` | TTS voice |
| `VIENEU_SPEED` | `1.0` | Playback speed |
| `VIENEU_STYLE` | `"friendly"` | Voice style |
| `VIENEU_TEMPERATURE` | `0.7` | Generation temperature |
| `VIENEU_STREAMING` | `true` | Enable streaming TTS |
| `TTS_OPENER_FIRST` | `true` | Opener before expressive |
| `TTS_EXPRESSIVE_FIRST_SENTENCE_TIMEOUT_S` | `15` | Expressive first sentence timeout |

### 19.7 TTS (Piper HTTP Fallback)

| Variable | Default | Mô tả |
|---|---|---|
| `PIPER_BASE_URL` | `""` | Piper server URL |
| `PIPER_VOICE` | `""` | Piper voice name |
| `PIPER_REQUEST_TIMEOUT_SECONDS` | `15` | Piper timeout |

### 19.8 TTS (Google)

| Variable | Default | Mô tả |
|---|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | `""` | Path to GCP credentials |
| `GOOGLE_TTS_VOICE` | `""` | Google TTS voice |
| `GOOGLE_STT_MODEL` | `""` | Google STT model |

### 19.9 Assistant Persona

| Variable | Default | Mô tả |
|---|---|---|
| `PERSONA_NAME` | `"Trợ lý AI của trường"` | Assistant name |
| `ASSISTANT_PROFILE` | `"config/assistant_school.yaml"` | Profile path |
| `RESPONSE_MAX_SENTENCES` | `5` | Hard sentence cap |
| `RESPONSE_MAX_WORDS` | `100` | Hard word cap |
| `CONVERSATION_MAX_TURNS` | `8` | Context window size |

### 19.10 STT

| Variable | Default | Mô tả |
|---|---|---|
| `STT_CANDIDATE` | `""` | STT candidate name |
| `WHISPER_MODEL` | `""` | Whisper model name |
| `WHISPER_MLX_MODEL` | `""` | MLX Whisper model |
| `WHISPER_NO_SPEECH_PROB` | `0.5` | No-speech threshold |
| `LOCAL_STT_BACKEND` | `""` | Backend (whisper/sherpa/mlx) |

### 19.11 VAD

| Variable | Default | Mô tả |
|---|---|---|
| `VAD_CONFIDENCE` | `0.5` | VAD confidence |
| `VAD_START_SECS` | `0.2` | Speech start threshold |
| `VAD_STOP_SECS` | `0.8` | Speech stop threshold |
| `VAD_MIN_VOLUME` | `0.6` | Min volume |

### 19.12 Wake Gate

| Variable | Default | Mô tả |
|---|---|---|
| `WAKE_MODE_ENABLED` | `false` | Enable idle/active gate |
| `IDLE_TIMEOUT_SECONDS` | `30` | Idle timeout |

### 19.13 Mock

| Variable | Default | Mô tả |
|---|---|---|
| `MOCK_AUTO_TRANSCRIBE` | `true` | Auto-send scripted transcripts |
| `MOCK_SCRIPTED_TRANSCRIPTS` | `...` | Pipe-separated test transcripts |

### 19.14 Device

| Variable | Default | Mô tả |
|---|---|---|
| `DEVICE_POLICY` | `"auto"` | Pytorch device policy |
| `PYTORCH_DEVICE` | `"auto"` | Pytorch device |
| `ALLOW_CPU_FALLBACK` | `true` | Allow CPU fallback |
| `LOG_DEVICE_DIAGNOSTICS` | `true` | Log device info |

### 19.15 Metrics

| Variable | Default | Mô tả |
|---|---|---|
| `METRICS_JSONL_PATH` | `artifacts/metrics.jsonl` | Metrics output path |

---

## 20. Các vấn đề đã biết & Hạn chế

### 20.1 Critical Fixes Đã Áp Dụng

| # | Vấn đề | Fix | File |
|---|---|---|---|
| 1 | `iceConfig` không ở top-level session response | Thêm `iceConfig` field | `main.py` |
| 2 | UDP bị chặn trên một số mạng WiFi | Fallback TURN TCP/TLS 443 | `turn_credentials.py` |
| 3 | TTS VieNeu warm-up chưa xong khi intro gửi | Retry 3×1.5s | `worker_factory.py` |
| 4 | `LOCAL_STT_MAX_SESSIONS=1` chặn device thứ 2 | Tăng lên 4 | `.env` |
| 5 | Circular import: turn_credentials → main | Tách `ice_utils.py` | Refactor |
| 6 | Cloudflared quick tunnel không ổn định | Auto-retry + restart | `start.sh` |

### 20.2 Hạn Chế Hiện Tại

| # | Hạn chế | Mức độ | Kế hoạch |
|---|---|---|---|
| 1 | **Quick tunnel URL thay đổi** mỗi lần restart | Trung bình | Named tunnel + custom domain |
| 2 | **49 env vars** — phức tạp khó bảo trì | Thấp | Audit unused, tạo `.env.example` |
| 3 | **Không có E2E tests** | Cao | Viết test WebRTC + ICE |
| 4 | **Không có cơ chế dọn artifacts** | Trung bình | Cron job dọn file >7 ngày |
| 5 | **Disk usage** — trước đây thường xuyên <500MB | Thấp | Đã cải thiện (13GB free) |
| 6 | **Không có horizontal scaling** | Thấp | Chưa cần cho deployment nhỏ |
| 7 | **Single point of failure** (1 MacBook) | Trung bình | Đã có auto-restart tunnel |
| 8 | **Admin dashboard chưa hoàn thiện auth** | Thấp | Token hết hạn không xử lý graceful |
| 9 | **Dashboard HTML gọi API trực tiếp** | Thấp | Cần thêm error handling |
| 10 | **Không có rate limiting** | Thấp | Chưa cần cho 4 sessions |

### 20.3 Technical Debt

1. **22+ file .md ở root** trước đây — đã dọn vào `docs/` và `reports/`
2. **14 scripts** trong `scripts/` — cần tổ chức lại
3. **Thư mục `reports/` vs `docs/`** chồng chéo
4. **Hard-coded constants** trong một số file (nên configurable)
5. **Mock providers** chỉ nên dùng trong tests, không production

---

## 21. Lộ trình nâng cấp

### 21.1 PR status (2026-07-31)

| PR | Mục tiêu | Trạng thái |
|---|---|---|
| PR-0 | Baseline | ✅ Done |
| PR-1 | Security hardening | ✅ Done |
| PR-2 | Session & resource lifecycle | ✅ Done |
| PR-3 | Barge-in & response lifecycle | ✅ Core done (interruption hooks → PR-5) |
| PR-4 | WebSocket RTVI | ✅ Done (feature-flagged, default off) |
| PR-5 | Benchmark & optimize M1 | 🔜 Engineering targets defined below |

### 21.2 Engineering targets (PR-5)

These are targets, not current claims. Benchmarks must be reproducible.

```text
Sherpa decode P95                    ≤ 300 ms
VAD end → LLM first accepted text    ≤ 1.0 s
First accepted text → first audio    ≤ 600 ms
VAD end → first audible audio        ≤ 1.6 s
Barge-in → audible stop P95          ≤ 250 ms
Stale output after cancel            = 0
Terminal event loss                  = 0
Task/connection leak                 = 0
```

### 21.3 Benchmark methodology

- Hardware: MacBook Air M1, 8GB RAM
- Python 3.12, Pipecat 1.6.0
- Model revisions locked in model manifest (section 1.2.1)
- Warm-up: 3 runs before measurement
- Datasets: VIVOS + in-domain school recordings
- Metrics: P50/P95/P99, RTF, RAM, CPU, thermal
- Only change defaults when 2-session gate passes without swap/throttle

### 21.1 Ngắn hạn (1-2 tuần)

- [ ] **Named tunnel:** Cấu hình `red-sea-f1c7` với custom domain → URL ổn định
- [ ] **`.env.example`:** Tạo file mẫu đầy đủ
- [ ] **Audit env vars:** Xác định unused, giảm từ 49 xuống ~35
- [ ] **E2E test:** Test WebRTC connection từ browser local
- [ ] **Artifacts cleanup:** Cron job hoặc startup script dọn file >7 ngày
- [ ] **Dọn thư mục:** Merge `reports/` vào `docs/`, tổ chức `scripts/`
- [ ] **Admin auth error handling:** Xử lý token hết hạn trong dashboard

### 21.2 Trung hạn (2-4 tuần)

- [ ] **Adaptive Routing (Phase 3):** Router/Planner model riêng
- [ ] **Advanced Expression Composer:** Biểu cảm robot phong phú hơn
- [ ] **User Memory:** Lưu thông tin người dùng qua các phiên
- [ ] **Multi-turn tools:** Tool execution với confirmation flow
- [ ] **Rate limiting:** Cho API endpoints
- [ ] **Health dashboard:** Monitoring metrics real-time

### 21.3 Dài hạn (1-3 tháng)

- [ ] **Multi-device sync:** Đồng bộ context giữa các thiết bị
- [ ] **Horizontal scaling:** Multiple workers, load balancing
- [ ] **Persistent sessions:** Lưu session state ra disk/DB
- [ ] **Production deployment:** Docker, cloud VPS, managed tunnel
- [ ] **Analytics:** Thống kê usage, popular queries, error rates
- [ ] **i18n:** Hỗ trợ thêm ngôn ngữ (English, v.v.)

### 21.4 Known Upgrade Risks

1. **VieNeu model update** → chạy benchmark TTS trước khi deploy
2. **Pipecat version bump** → test pipeline end-to-end
3. **Python version upgrade** → kiểm tra ONNX + sherpa-onnx compatibility
4. **Cloudflare TURN API changes** → theo dõi CF changelog
5. **macOS update** → test MLX + ONNX runtime

---

## Phụ lục A: Dependency Graph

```
app/main.py
├── app/config.py
│   ├── config/profiles.yaml
│   └── .env
├── app/sessions.py
├── app/auth.py
├── app/admin.py
│   └── .env (read/write)
├── app/pipecat_runtime/turn_credentials.py
│   └── Cloudflare TURN API
├── app/pipecat_runtime/worker_factory.py
│   ├── app/pipecat_runtime/pipeline_factory.py
│   │   ├── app/core/system_prompt.py
│   │   │   └── config/assistant_school.yaml
│   │   ├── app/core/context_manager.py
│   │   ├── app/core/knowledge.py
│   │   │   └── knowledge/school/*.yaml
│   │   ├── app/core/glossary.py
│   │   │   └── config/glossary.yaml
│   │   ├── app/pipecat_runtime/sherpa_stt.py
│   │   ├── app/pipecat_runtime/vieneu_engine.py
│   │   ├── app/pipecat_runtime/two_tier_tts.py
│   │   ├── app/processors/*
│   │   └── app/tools/gateway.py
│   └── app/pipecat_runtime/rtvi.py
│       └── app/robot/messages.py
└── app/pipecat_runtime/metrics.py
    └── artifacts/metrics.jsonl
```

## Phụ lục B: Port Map

| Port | Service | Protocol |
|---|---|---|
| 8000 | FastAPI server | HTTPS (LAN) / HTTP (tunnel target) |
| 3478 | STUN/TURN | UDP + TCP |
| 80 | TURN fallback | TCP |
| 5349 | TURN TLS | TCP |
| 443 | TURN TLS (unblockable) | TCP |

## Phụ lục C: Quick Reference Commands

```bash
# Start
cd robot-ai-host && ./start.sh

# Health check
curl -sk https://127.0.0.1:8000/health

# Test TURN
curl -sk -X POST https://127.0.0.1:8000/v1/devices/register \
  -H "Content-Type: application/json" \
  -d '{"provisioning_secret":"dev-provisioning-secret","device_id":"test","device_type":"browser"}'

# Run tests
PYTHONPATH=. .venv-hybrid/bin/pytest tests/ -v

# View metrics
tail -f artifacts/metrics.jsonl

# Check disk
df -h /
```

---

> **Document version:**0.1.0**Baseline:** 2026-07-31, commit `ef1580b`**Next review:** PR-1 (security hardening)
