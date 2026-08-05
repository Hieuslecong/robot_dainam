# Hướng dẫn debug kết nối WebRTC

## Kiểm tra nhanh

```bash
# 1. Server có chạy không?
curl -sk https://127.0.0.1:8000/health

# 2. Tunnel có sống không?
curl -sk https://<tunnel-url>/health

# 3. TURN có hoạt động không?
curl -sk -X POST https://127.0.0.1:8000/v1/devices/register \
  -H "Content-Type: application/json" \
  -d '{"provisioning_secret":"dev-provisioning-secret","device_id":"diag","device_name":"Diag","device_type":"browser"}'
# → Lấy access_token, rồi:
curl -sk -X POST https://127.0.0.1:8000/v1/sessions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"profile":"hybrid_local_vi","device_id":"diag","language":"vi-VN","transport":"webrtc"}'
# → Kiểm tra response có "iceConfig.iceServers" với Cloudflare TURN URLs không
```

## Các lỗi thường gặp

### "Kết nối thất bại" trên điện thoại

| Nguyên nhân | Cách kiểm tra | Fix |
|---|---|---|
| Tunnel chết | `curl <tunnel-url>/health` không response | `./start.sh` |
| TURN credential hết hạn | Session > 1h, `turnExpiresAt` đã qua | Tạo session mới |
| UDP bị chặn | Test STUN timeout | Dùng TURN TLS 443 (đã cấu hình) |
| `iceConfig` thiếu | Response không có field `iceConfig` ở top-level | Đã fix trong `main.py` |
| MAX_SESSIONS | Log: `max_sessions_reached` | Tăng `MAX_SESSIONS` trong `.env` |
| LOCAL_STT_MAX | Log: `local_stt_max_sessions` | Tăng `LOCAL_STT_MAX_SESSIONS` |

### Không có âm thanh

| Triệu chứng | Nguyên nhân | Fix |
|---|---|---|
| `vieneu_warming_up` | TTS chưa load xong | Đã fix: retry 3 lần |
| ICE connected nhưng không nghe | Audio track không được gán | Kiểm tra `onTrack` handler |
| `Data channel not ready` | Kênh data chưa mở | Bình thường, tự resolve |

### Tunnel không ổn định

| Triệu chứng | Nguyên nhân | Fix |
|---|---|---|
| `network is unreachable` | Mạng chặn UDP | Dùng `--protocol http2` |
| `connection reset by peer` | Cloudflare API từ chối | Retry, đổi mạng |
| `Unauthorized: Tunnel not found` | Quick tunnel hết hạn | Restart tunnel |

## Log quan trọng

```bash
# Xem log server
tail -f <server output>

# Các dòng cần chú ý:
turn_credential_generated    # ✅ TURN OK
turn_credential_failed       # ❌ TURN fail → kiểm tra API key
vieneu_loaded                # ✅ TTS sẵn sàng
vieneu_warming_up            # ⚠️ TTS đang load (bình thường)
client_connected             # ✅ WebRTC connected
session_heartbeat_expired    # ❌ Mất kết nối
max_sessions_reached         # ❌ Quá giới hạn
```

## Test TURN thủ công

```bash
# Gọi Cloudflare TURN API trực tiếp
curl -X POST "https://rtc.live.cloudflare.com/v1/turn/keys/$KEY_ID/credentials/generate" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ttl": 3600}'

# Response mong đợi:
# {"iceServers": {"username": "...", "credential": "...", "urls": ["stun:...", "turn:...", "turns:..."]}}
```

## Test UDP/STUN

```bash
python3 -c "
import socket, struct
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(3)
msg = struct.pack('>HHI12s', 0x0001, 0x0000, 0x2112A442, b'\x00'*12)
s.sendto(msg, ('stun.l.google.com', 19302))
try:
    data, addr = s.recvfrom(1024)
    print(f'UDP OK: {addr}')
except socket.timeout:
    print('UDP BLOCKED')
"
```
