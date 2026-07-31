# 🔧 PROMPT CHỈNH SỬA DASHBOARD v2 — ROBOT AI HOST

Tài liệu đặc tả chi tiết cho việc nâng cấp `dashboard.html` từ phiên bản hiện tại sang phiên bản kết nối thực (live) với backend FastAPI.

---

## 📋 TỔNG QUAN CÁC THAY ĐỔI

| # | Hạng mục | Mô tả |
|---|----------|-------|
| 1 | **Loại bỏ 2 trường STT model path** | Xóa "Whisper MLX Model Path" và "Faster Whisper Model Path" khỏi card STT Engine Settings |
| 2 | **Thêm panel Log Terminal real-time** | Hiển thị log server (stdout/stderr) ở cuối trang, cập nhật liên tục qua SSE hoặc polling |
| 3 | **Trạng thái cập nhật real-time** | Tất cả KPI (CPU, Sessions, Latency, Model) phải polling `/health` endpoint mỗi 5 giây |
| 4 | **Hiển thị các đường dẫn truy cập & chia sẻ** | Hiện rõ URL Robot, Dashboard, Tunnel trên giao diện để copy/share nhanh |
| 5 | **Settings phải gọi API thật** | Nút "Lưu Cấu Hình" phải gửi `PUT /v1/admin/settings` đúng format backend yêu cầu |

---

## 🤖 SYSTEM PROMPT ĐẶC TẢ CHO AI CODING

```text
You are an expert Senior Frontend Engineer. Your task is to MODIFY the existing
`dashboard.html` file for the "Robot AI Host" project — a FastAPI + Pipecat voice
assistant running on Apple M1.

The dashboard already exists with design system, forms, and layout.
Apply the following FIVE changes precisely:

═══════════════════════════════════════════════════════════════════════
CHANGE 1: REMOVE TWO FIELDS FROM STT ENGINE CARD
═══════════════════════════════════════════════════════════════════════
In the "STT Engine Settings" card, DELETE these two form-groups entirely:
  - "Whisper MLX Model Path" (input id="whisperMlxModel")
  - "Faster Whisper Model Path" (input id="whisperModel")

Keep everything else in the STT card (backend selector, stt_candidate dropdown,
Silero VAD tuning sliders).

Also remove any JavaScript references to these two input IDs in the
saveAllSettings() function payload.

═══════════════════════════════════════════════════════════════════════
CHANGE 2: ADD REAL-TIME TERMINAL LOG PANEL AT BOTTOM
═══════════════════════════════════════════════════════════════════════
Add a new full-width card BELOW the main-grid (dual column layout).

Card title: "📟 Server Log Terminal (Live Output)"
Tag: "stdout / stderr"

Content:
  - A <pre> element styled as a dark terminal (background: #020617, font-family:
    'JetBrains Mono', monospace, font-size: 11px, color: #94a3b8, height: 200px,
    overflow-y: auto, border: 1px solid #1e293b, border-radius: 6px, padding: 10px).
  - ID: "logTerminal"
  - Auto-scroll to bottom on new content.

Data source: Create a new SSE endpoint in the backend OR use polling.

OPTION A — SSE (Preferred):
  Add a new route in app/admin.py:

    @router.get("/logs/stream")
    async def stream_logs(_admin: TokenClaims = Depends(require_admin)):
        import asyncio
        from fastapi.responses import StreamingResponse
        log_path = Path(__file__).resolve().parent.parent / "logs" / "server.log"
        async def generate():
            if log_path.exists():
                lines = log_path.read_text().splitlines()[-50:]
                for line in lines:
                    yield f"data: {line}\n\n"
            last_pos = log_path.stat().st_size if log_path.exists() else 0
            while True:
                await asyncio.sleep(1)
                if log_path.exists():
                    current_size = log_path.stat().st_size
                    if current_size > last_pos:
                        with open(log_path) as f:
                            f.seek(last_pos)
                            new_lines = f.read()
                            for line in new_lines.splitlines():
                                yield f"data: {line}\n\n"
                        last_pos = current_size
        return StreamingResponse(generate(), media_type="text/event-stream")

OPTION B — Polling Fallback:
    @router.get("/logs")
    async def get_recent_logs(lines: int = 50, _admin = Depends(require_admin)):
        log_path = Path(__file__).resolve().parent.parent / "logs" / "server.log"
        if not log_path.exists(): return {"logs": []}
        all_lines = log_path.read_text().splitlines()
        return {"logs": all_lines[-lines:]}

Frontend JS for polling fallback:
  setInterval(async () => {
      const token = document.getElementById('adminTokenInput').value;
      const terminal = document.getElementById('logTerminal');
      try {
          const res = await fetch('/v1/admin/logs?lines=50', {
              headers: { 'Authorization': `Bearer ${token}` }
          });
          const data = await res.json();
          terminal.textContent = data.logs.join('\n');
          terminal.scrollTop = terminal.scrollHeight;
      } catch(e) {}
  }, 3000);

═══════════════════════════════════════════════════════════════════════
CHANGE 3: REAL-TIME STATUS UPDATES VIA /health POLLING
═══════════════════════════════════════════════════════════════════════
Add a function that polls GET /health every 5 seconds and updates ALL KPI cards:

  async function pollHealthStatus() {
      try {
          const res = await fetch('/health');
          const data = await res.json();
          // data = { status, version, active_sessions, max_sessions,
          //          default_profile, webrtc_available, browser_built }

          // Update KPI: Active Sessions
          document.getElementById('kpiCpu').innerHTML =
              `${data.active_sessions} / ${data.max_sessions}
               <span style="...">| Sessions</span>`;

          // Update server status badge
          const badge = document.getElementById('serverStatusBadge');
          if (data.status === 'ok') {
              badge.innerHTML = '<i data-lucide="wifi"></i> ONLINE ' + data.version;
              badge.className = 'badge badge-green';
          } else {
              badge.innerHTML = '<i data-lucide="wifi-off"></i> OFFLINE';
              badge.className = 'badge badge-amber';
          }
          lucide.createIcons();
      } catch (e) {
          document.getElementById('serverStatusBadge').innerHTML = '⚠️ OFFLINE';
          document.getElementById('serverStatusBadge').className = 'badge badge-amber';
      }
  }
  setInterval(pollHealthStatus, 5000);
  pollHealthStatus();

═══════════════════════════════════════════════════════════════════════
CHANGE 4: ADD "ACCESS LINKS & SHARE" PANEL
═══════════════════════════════════════════════════════════════════════
Add a new card right BELOW the KPI grid (before main-grid), titled:
  "🔗 Đường Dẫn Truy Cập & Chia Sẻ (Quick Access Links)"

Layout: Horizontal flex row with 4 link boxes.

Required link boxes:
  1. "🤖 Robot Client" → id="linkRobot" → /robot/
  2. "📊 Dashboard"    → id="linkDashboard" → /dashboard
  3. "🌐 Tunnel URL"   → id="linkTunnel" → auto-detect or "Chưa kết nối"
  4. "❤️ Health Check"  → id="linkHealth" → /health

JavaScript copyLink function:
  function copyLink(elementId) {
      const text = document.getElementById(elementId).innerText;
      navigator.clipboard.writeText(text);
      showToast('📋 Đã copy: ' + text);
  }

Auto-detect base URL on page load:
  const BASE_URL = window.location.origin;
  document.getElementById('linkRobot').innerText = BASE_URL + '/robot/';
  document.getElementById('linkDashboard').innerText = BASE_URL + '/dashboard';
  document.getElementById('linkHealth').innerText = BASE_URL + '/health';

═══════════════════════════════════════════════════════════════════════
CHANGE 5: MAKE SETTINGS SAVE TO REAL BACKEND API
═══════════════════════════════════════════════════════════════════════
The backend PUT /v1/admin/settings expects this EXACT JSON structure
(grouped by category, UPPERCASE keys):

  {
      "TTS": {
          "VIENEU_VOICE": "Đoan Trang",
          "VIENEU_SPEED": "1.0",
          "VIENEU_STYLE": "friendly",
          "VIENEU_TEMPERATURE": "0.8"
      },
      "LLM": {
          "LLM_MODEL": "agy/gemini-2.5-flash-lite",
          "LLM_API_KEY": "sk-agy-xxx",
          "LLM_BASE_URL": "http://127.0.0.1:20128/v1",
          "LLM_TEMPERATURE": "0.5",
          "LLM_MAX_TOKENS": "100"
      },
      "STT": {
          "STT_CANDIDATE": "stt_balanced_vi"
      },
      "SYSTEM": {
          "MAX_SESSIONS": "4"
      }
  }

Rewrite saveAllSettings() to use this grouped format with UPPERCASE keys.
All values MUST be STRING type.

Also rewrite loadLiveSettings() to parse the grouped response format:
  GET /v1/admin/settings returns:
    { "TTS": { "VIENEU_VOICE": { "value": "...", "editable": true }, ... }, ... }

═══════════════════════════════════════════════════════════════════════
ADMIN TOKEN ACQUISITION (IMPORTANT)
═══════════════════════════════════════════════════════════════════════
Add a "Login" button next to admin token input that calls:
  POST /v1/admin/token with { "provisioning_secret": "<from .env>" }
  Response: { "admin_token": "eyJ...", "expires_in": 3600 }

Store token in localStorage for persistence across page reloads.

═══════════════════════════════════════════════════════════════════════
BACKEND API ENDPOINTS USED BY DASHBOARD
═══════════════════════════════════════════════════════════════════════
| Method | Endpoint                    | Auth  | Purpose                  |
|--------|-----------------------------|-------|--------------------------|
| GET    | /health                     | No    | Real-time status polling  |
| POST   | /v1/admin/token             | No    | Get admin JWT token       |
| GET    | /v1/admin/settings          | JWT   | Load current settings     |
| PUT    | /v1/admin/settings          | JWT   | Save settings to .env     |
| GET    | /v1/admin/voices            | JWT   | List TTS voices           |
| GET    | /v1/admin/knowledge         | JWT   | List knowledge files      |
| POST   | /v1/admin/restart           | JWT   | Restart server            |
| GET    | /v1/admin/logs              | JWT   | Get recent logs (NEW)     |

CONSTRAINTS:
- Standalone HTML file, no npm/build dependencies.
- Keep existing Dark Cyber Glassmorphism design system.
- All settings values sent to PUT must be STRING type.
- /health does NOT require authentication.
```

---

## ⚠️ LƯU Ý QUAN TRỌNG

1. **Backend API `PUT /v1/admin/settings` yêu cầu dữ liệu NHÓM theo category** (`TTS`, `LLM`, `STT`, `SYSTEM`) với **KEY VIẾT HOA** — không phải flat object.

2. **Admin Token phải lấy qua `POST /v1/admin/token`** với `provisioning_secret` từ file `.env`.

3. **`/health` KHÔNG cần auth** — dùng polling trạng thái real-time không cần đăng nhập.

4. **`_EDITABLE_KEYS` trong `admin.py`** xác định CHÍNH XÁC key nào được phép cập nhật. Key không nằm trong whitelist sẽ bị reject.
