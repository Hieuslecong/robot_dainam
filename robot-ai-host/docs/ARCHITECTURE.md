# Robot AI Host — Kiến trúc kết nối WebRTC qua Cloudflare

## Tổng quan

```
Điện thoại (4G/WiFi)
    │
    ├─ HTTPS signaling ──→ Cloudflare Tunnel (HTTP2) ──→ FastAPI :8000
    │   • POST /v1/devices/register
    │   • POST /v1/sessions         → trả về ICE servers + SDP URL
    │   • POST /v1/sessions/{id}/api/offer
    │   • PATCH /v1/sessions/{id}/api/offer   (ICE candidates)
    │   • POST /v1/sessions/{id}/heartbeat
    │
    └─ WebRTC media ──→ direct (nếu NAT cho phép)
                     ──→ Cloudflare TURN relay (nếu direct thất bại)
                         • UDP 3478
                         • TCP 3478
                         • TCP 80
                         • TLS 5349
                         • TLS 443  ← luôn hoạt động, kể cả mạng chặn UDP
```

## Thành phần

| Thành phần | Vai trò |
|---|---|
| **FastAPI** (`app/main.py`) | REST API: đăng ký thiết bị, tạo session, SDP signaling |
| **Pipecat** (`SmallWebRTCTransport`) | WebRTC transport: audio realtime |
| **Cloudflare Tunnel** | Proxy HTTP/HTTPS công khai cho signaling |
| **Cloudflare TURN** | Relay media khi direct connection thất bại |
| **STT** (Sherpa Zipformer) | Nhận dạng tiếng Việt |
| **LLM** (Gemini 2.5 Flash Lite) | Xử lý hội thoại |
| **TTS** (VieNeu two-tier) | Tổng hợp giọng nói |

## Luồng kết nối

### 1. Tạo session

```
Client                                Server
  │                                     │
  ├─ POST /v1/devices/register ────────→
  │  {provisioning_secret, device_id}   │
  │                                     ├─ Xác thực secret
  │←─ {access_token} ──────────────────┤
  │                                     │
  ├─ POST /v1/sessions ────────────────→
  │  {profile, device_id}               │
  │  Authorization: Bearer <token>      │
  │                                     ├─ Tạo JWT connection token
  │                                     ├─ Gọi Cloudflare TURN API
  │                                     │  POST /v1/turn/keys/{id}/credentials/generate
  │                                     │  → {username, credential, urls}
  │                                     ├─ Trả về ICE servers
  │←─ {                                 │
  │     session_id, webrtcUrl,          │
  │     iceConfig: {                    │  ← KEY: Pipecat client đọc field này
  │       iceServers: [                 │
  │         {urls: "stun:..."},         │
  │         {urls: ["turn:...", ...],   │
  │          username, credential}      │
  │       ]                             │
  │     }                               │
  │   } ───────────────────────────────┤
```

### 2. WebRTC negotiation

```
Client                                Server
  │                                     │
  ├─ POST /v1/sessions/{id}/api/offer ─→
  │  {sdp, type:"offer"}               │
  │                                     ├─ Tạo SmallWebRTCConnection
  │                                     ├─ Tạo pipeline (STT→LLM→TTS)
  │←─ {sdp, type:"answer"} ───────────┤
  │                                     │
  ├─ PATCH .../api/offer ──────────────→
  │  {candidates: [...]}               │
  │                                     ├─ ICE negotiation
  │←─ 200 OK ─────────────────────────┤
  │                                     │
  │═══════ WebRTC connected ═══════════│
  │  audio hai chiều                    │
```

### 3. ICE candidate selection

```
1. Host candidates (IP local) → ưu tiên cao nhất
2. srflx candidates (STUN)     → nếu NAT cho phép
3. Relay candidates (TURN)     → nếu direct thất bại
   • TURN UDP → nhanh nhất nếu UDP không bị chặn
   • TURN TCP → fallback
   • TURN TLS 443 → luôn hoạt động (không bị firewall chặn)
```

## Cấu hình

### .env

```env
# Cloudflare TURN
CLOUDFLARE_TURN_KEY_ID=d9f1fa268a5dea6a5317f53f5fece0f9
CLOUDFLARE_TURN_API_TOKEN=<secret>
CLOUDFLARE_TURN_TTL_SECONDS=3600

# ICE policy
WEBRTC_ICE_POLICY=all          # all | relay
WEBRTC_FORCE_RELAY=false       # true = chỉ dùng TURN (test)

# Transport toggles
WEBRTC_ENABLE_STUN=true
WEBRTC_ENABLE_TURN_UDP=true
WEBRTC_ENABLE_TURN_TCP=true
WEBRTC_ENABLE_TURN_TLS=true

# Session limits
MAX_SESSIONS=4
LOCAL_STT_MAX_SESSIONS=4
```

## Các vấn đề đã gặp & fix

### 1. UDP bị chặn trên một số mạng WiFi
- **Triệu chứng**: Cloudflared QUIC timeout, STUN timeout, ICE chỉ có host candidates
- **Fix**: Fallback sang TURN TCP/TLS 443. Cloudflare TURN TLS 443 luôn hoạt động.

### 2. TURN credential không được client sử dụng
- **Triệu chứng**: Server gửi `webrtc.ice_servers` nhưng Pipecat client-js đọc `iceConfig.iceServers` ở top-level
- **Fix**: Thêm field `iceConfig` vào top-level của session response (`app/main.py:383`)

### 3. TTS VieNeu warm-up chưa xong khi intro được gửi
- **Triệu chứng**: `vieneu_warming_up` → intro bị fail → không có âm thanh
- **Fix**: Retry 3 lần, mỗi lần đợi 1.5s (`app/pipecat_runtime/worker_factory.py:163-172`)

### 4. LOCAL_STT_MAX_SESSIONS=1 chặn thiết bị thứ 2
- **Triệu chứng**: Thiết bị thứ 2 báo "max sessions reached"
- **Fix**: Tăng lên 4 (`.env`)

### 5. Cloudflared quick tunnel không ổn định
- **Triệu chứng**: Tunnel chết sau 1-2 phút trên một số mạng
- **Workaround**: `start.sh` tự động retry tunnel 3 lần, auto-restart khi rớt
- **Production fix**: Dùng named tunnel với domain riêng

## Vận hành

### Khởi động
```bash
cd robot-ai-host
./start.sh
```

### Kiểm tra
```bash
# Health check
curl https://<tunnel-url>/health

# Xem ICE servers được trả về
curl -X POST https://<tunnel-url>/v1/devices/register \
  -H "Content-Type: application/json" \
  -d '{"provisioning_secret":"dev-provisioning-secret","device_id":"test","device_name":"test","device_type":"browser"}'

# Lấy token, rồi:
curl -X POST https://<tunnel-url>/v1/sessions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"profile":"hybrid_local_vi","device_id":"test","language":"vi-VN","transport":"webrtc"}'
```

### Log quan trọng
```
turn_credential_generated  → TURN credential được tạo thành công
vieneu_loaded              → TTS đã sẵn sàng
client_connected           → WebRTC đã kết nối
ICE connection state       → checking → connected / failed
```

## File liên quan

| File | Vai trò |
|---|---|
| `app/main.py` | API endpoints, tạo session, trả về ICE servers |
| `app/config.py` | Cấu hình settings |
| `app/pipecat_runtime/turn_credentials.py` | Gọi Cloudflare TURN API, sinh credential |
| `app/pipecat_runtime/worker_factory.py` | Tạo pipeline worker, intro retry |
| `app/pipecat_runtime/pipeline_factory.py` | Tạo pipeline STT→LLM→TTS |
| `app/sessions.py` | Quản lý session, giới hạn max |
| `clients/browser/` | Web client cho điện thoại |
| `clients/desktop_robot_emulator/` | Robot face (auto-connect) |
| `cloudflared-config.yml` | Config named tunnel |
| `start.sh` | Script khởi động server + tunnel |
| `.env` | Biến môi trường |
