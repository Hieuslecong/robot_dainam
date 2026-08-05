# Kế hoạch: Dashboard `/client/` + Robot `/robot/` tối giản

## Pipeline — Không cần chỉnh sửa

```
transport.input() → STT → STTGuard → WakeGate → UserAggregator
→ Compactor → Grounding → SmallTalkBypass → LLM
→ StreamDedup → ResponsePolicy → TTS → transport.output()
→ AssistantAggregator
```

Pipeline đã hoàn chỉnh, không cần thay đổi.

---

## 1. `/robot/` — tối giản

**Mục tiêu:** Chỉ có connect/disconnect, không có config UI.

**Hiện tại:** Đã làm xong (auto-connect, controls ẩn). ✅ Không cần làm gì thêm.

---

## 2. `/client/` → Dashboard quản lý

**Mục tiêu:** Trang web quản lý tất cả cài đặt hệ thống, tách biệt với voice client.

### Cấu trúc dashboard

```
/client/                          ← Dashboard (trang mới)
├── Tab 1: Voice (TTS)
│   ├── Giọng nói (voice): dropdown (Đoan Trang, ...)
│   ├── Tốc độ (speed): slider 0.5-2.0
│   ├── Phong cách (style): dropdown (cheerful, neutral, ...)
│   └── Nhiệt độ (temperature): slider 0.1-2.0
│
├── Tab 2: Model (LLM)
│   ├── Model: text input (agy/gemini-2.5-flash-lite, ...)
│   ├── API Key: password input
│   ├── Base URL: text input
│   ├── Temperature: slider
│   └── Max tokens: number input
│
├── Tab 3: Speech (STT)
│   ├── STT Candidate: dropdown (stt_streaming_vi, ...)
│   └── Language: dropdown
│
├── Tab 4: Knowledge
│   ├── Upload file (.yaml, .txt)
│   ├── List files in knowledge/
│   └── Delete file
│
└── Tab 5: System
    ├── Max sessions: number
    ├── Heartbeat timeout: number
    └── Restart server button
```

### Backend API mới

```
GET  /v1/admin/settings          → trả về tất cả settings hiện tại
PUT  /v1/admin/settings          → cập nhật settings (ghi .env + reload)
GET  /v1/admin/voices            → danh sách voice có sẵn
POST /v1/admin/knowledge/upload  → upload file vào knowledge/
GET  /v1/admin/knowledge         → liệt kê file trong knowledge/
DELETE /v1/admin/knowledge/{name} → xóa file
POST /v1/admin/restart           → restart server (soft reload)
```

### Implementation steps

1. Tạo `clients/browser/dashboard.html` — giao diện dashboard
2. Tạo `app/admin.py` — API endpoints quản lý settings
3. Mount admin router vào `main.py`
4. Giữ `/client/` trỏ về dashboard mới
5. Voice page hiện tại → chuyển thành `/client/chat` (giữ lại để test voice)

### Files cần tạo/sửa

| File | Action |
|---|---|
| `clients/browser/dashboard.html` | Tạo mới |
| `app/admin.py` | Tạo mới |
| `app/main.py` | Thêm admin router |
| `clients/browser/index.html` | Không đổi (voice client, sẽ mount ở `/client/chat`) |
