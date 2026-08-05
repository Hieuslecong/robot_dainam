# API

## Authentication

1. `POST /v1/devices/register` với provisioning secret.
2. Dùng JWT trả về trong `Authorization: Bearer <token>`.
3. `POST /v1/sessions` trả thêm connection token ngắn hạn nằm trong `webrtcUrl`.

## POST /v1/devices/register

```json
{
  "device_id": "desktop-001",
  "device_type": "desktop_browser_emulator",
  "firmware_version": "0.2.0",
  "provisioning_secret": "dev-provisioning-secret",
  "capabilities": {"audio_input": true, "audio_output": true}
}
```

## POST /v1/sessions

```json
{
  "device_id": "desktop-001",
  "profile": "mock",
  "language": "vi-VN",
  "transport": "webrtc"
}
```

`profile` có thể bỏ trống để dùng `DEFAULT_PROFILE`.

Response tương thích `SmallWebRTCTransport`:

```json
{
  "session_id": "sess_...",
  "status": "created",
  "expires_in": 3600,
  "webrtcUrl": "http://127.0.0.1:8000/v1/sessions/sess_.../api/offer?access_token=...",
  "webrtc": {"url": "...", "ice_servers": []}
}
```

## WebRTC signaling

- `POST /v1/sessions/{id}/api/offer`
- `PATCH /v1/sessions/{id}/api/offer`

Pipecat Client SDK gọi các endpoint này thông qua `webrtcUrl`; application code không tự tạo SDP.

## Session endpoints

- `GET /v1/sessions/{id}`
- `POST /v1/sessions/{id}/heartbeat`
- `DELETE /v1/sessions/{id}`

## Metrics

```http
GET /v1/metrics?session_id=<optional>&profile=<optional>
```

Mỗi metric trả `count`, `p50`, `p90`, `p95`, `max`.

## Robot custom message

Server message data:

```json
{
  "type": "robot.behavior",
  "session_id": "sess_...",
  "data": {
    "behavior_id": "...",
    "name": "greet",
    "emotion": "friendly",
    "intensity": 0.5,
    "duration_ms": 700
  }
}
```

Client ACK:

```json
{
  "behavior_id": "...",
  "status": "completed",
  "duration_ms": 700
}
```

Allowlist expressive: `nod`, `shake_head`, `greet`, `happy`, `sad`, `confused`.
