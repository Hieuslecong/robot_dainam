# 🚀 PROMPT CHI TIẾT & ĐẶC TẢ THIẾT KẾ DASHBOARD "ROBOT AI HOST"

Tài liệu này chứa bộ **Prompts chi tiết**, **Hệ thống bảng màu (Color System)** và **Mã nguồn HTML/CSS/JS mẫu** dùng để phát triển giao diện quản trị tinh gọn, tập trung vào cấu hình & kiểm thử mô hình LLM cho dự án Robot AI Host (Mây Mây).

---

## 🎨 1. HỆ THỐNG BẢNG MÀU & NGUYÊN TẮC THIẾT KẾ (DESIGN SYSTEM)

Giao diện áp dụng phong cách **Dark Cyber Glassmorphism** tinh gọn, tương phản cao, tối ưu diện tích hiển thị và giảm tải CPU/RAM cho máy chủ MacBook Air M1.

| Thành phần | Mã Màu (HEX) | Mô tả & Ý nghĩa |
| :--- | :--- | :--- |
| **Background (Nền tối)** | `#0B0F19` | Nền tối sâu, giảm mỏi mắt, tiết kiệm năng lượng màn hình. |
| **Card Fill (Thẻ chứa)** | `rgba(15, 23, 42, 0.85)` | Lớp kính mờ kẹp viền, tạo độ sâu giao diện mà không làm nặng DOM. |
| **Card Border (Viền)** | `#1E293B` | Đường viền mảnh định hình các khối dữ liệu. |
| **Primary Accent (Indigo)** | `#6366F1` | Đại diện cho mô hình trí tuệ nhân tạo (LLM Workbench). |
| **Secondary Accent (Cyan)** | `#38BDF8` | Đại diện cho kết nối WebRTC & độ trễ mạng thời gian thực. |
| **Success Status (Emerald)**| `#34D399` | Trạng thái hệ thống hoạt động tốt (Ping 200 OK, Low Latency). |
| **Alert/Danger (Red/Amber)**| `#EF4444` / `#FBBF24`| Cảnh báo quá tải Session hoặc lỗi kết nối Endpoint. |
| **Text Main / Muted** | `#F8FAFC` / `#94A3B8`| Màu chữ chính trắng sáng và màu phụ xám trung tính dễ đọc. |

---

## 🖼️ 2. BỘ PROMPT TẠO HÌNH ẢNH MOCKUP UI (MIDJOURNEY / FLUX.1)

> Dùng đoạn prompt tiếng Anh dưới đây dán vào Midjourney v6, Flux.1 hoặc DALL-E 3 để tạo hình ảnh thiết kế UI chuẩn Figma:

```text
A professional, ultra-clean, streamlined dark-mode AI Admin Dashboard UI/UX interface for an AI Voice Assistant named "May May". Minimalist SaaS workbench style, dark slate background (#0B0F19) with glowing cyan (#38BDF8), indigo (#6366F1), and emerald green (#34D399) accents. High-density layout with ZERO clutter.

Top Header Bar: Displays "ROBOT AI HOST — LLM & CONTROL WORKBENCH", Apple M1 hardware stats (28% CPU, 5.2GB RAM), Latency P95 (1,240 ms), Current Model "Gemini 2.5 Flash Lite", and Active Sessions "2/4".

Two-Column Asymmetric Workbench Layout:
- Left Column (LLM Workbench & Instant Ping): Preset model dropdown selector, inputs for LLM_MODEL, LLM_BASE_URL, LLM_API_KEY, Temperature (0.5), Max Tokens (100). Below it, a compact "Instant LLM Test Ping" box showing "Status: 200 OK", "TTFB: 380ms", and "Speed: 42 tokens/sec" with a green [Test Endpoint] button.
- Right Column (Operations & Persona): System Prompt editor card showing persona "May May" with a Token Budget meter (520/800 tokens), VieNeu TTS Voice engine selector with [Test Voice] button, School Knowledge Base YAML file table, and Active WebRTC session list.

Crisp typography, sharp vector borders, clean data tables, modern UI design, Figma presentation screenshot style, 8k resolution, photorealistic rendering --ar 16:9 --v 6.0
```

---

## 🤖 3. SYSTEM PROMPT CHO AI CODING (CURSOR / CLAUDE 3.5 SONNET / GPT-4O)

> Dán đoạn prompt dưới đây vào Cursor, Claude 3.5 Sonnet hoặc GPT-4o để yêu cầu AI sinh mã nguồn tự động:

```text
You are an expert Senior UI/UX Frontend Engineer specializing in high-performance AI Management Dashboards.

Your task is to build a sleek, highly functional, and extremely streamlined Admin Dashboard for an AI Voice Assistant project named "Robot AI Host" (running locally on Apple M1, FastAPI, Pipecat, Sherpa-ONNX STT, and VieNeu TTS).

TECHNICAL & UI CONSTRAINTS:
1. Theme & Style: Dark Slate theme (Background: #0B0F19, Card Fill: rgba(15, 23, 42, 0.85), Borders: #1E293B). Accents: Cyan (#38BDF8), Indigo (#6366F1), Emerald (#34D399).
2. Layout Principles: Zero clutter. Single-page view (no vertical scrolling required). High data density, no 3D animated avatars, no long pipeline diagrams, no heavy chat playgrounds.

REQUIRED DASHBOARD COMPONENTS:
1. TOP HEADER & KPI STRIP:
   - System title: "ROBOT AI HOST — LLM & CONTROL WORKBENCH" | Status: ONLINE v0.1.0
   - 4 Compact KPI Cards:
     a) M1 Hardware: 28% CPU | 5.2GB / 8GB RAM.
     b) P95 Latency: 1,240 ms (VAD Stop -> First Audio).
     c) Current LLM: Gemini 2.5 Flash Lite (AGY Endpoint :20128).
     d) Grounding & Safety: 100% Grounded (4 YAML files | 0 Violations).
   - Action Buttons: [Save Settings] (Primary) and [Restart Server] (Danger).

2. LEFT COLUMN: LLM WORKBENCH & INSTANT PING (55% Width):
   - Model Configuration Card:
     * Preset Dropdown: 
       - "Gemini 2.5 Flash Lite (AGY Local Endpoint)" -> sets model: "agy/gemini-2.5-flash-lite", url: "http://127.0.0.1:20128/v1"
       - "Gemini 1.5 Flash (Direct Google API)" -> sets model: "gemini-1.5-flash", url: "https://generativelanguage.googleapis.com/v1beta/openai/"
       - "Llama 3 8B (Local Ollama / vLLM)" -> sets model: "llama3:8b-instruct", url: "http://127.0.0.1:11434/v1"
     * Inputs for: LLM_MODEL, LLM_BASE_URL, LLM_API_KEY (masked), Temperature (default 0.5), Max Tokens (default 100), Timeout (30s).
   - Instant LLM Health Ping Box:
     * Single input line for test query + [🚀 Test Endpoint] button.
     * Metrics output row: Status (200 OK), TTFB (380 ms), Speed (42 tokens/sec), Token Usage (48 in / 32 out).

3. RIGHT COLUMN: PERSONA, VOICE & OPERATIONS (45% Width):
   - Persona & System Prompt Editor:
     * Compact textarea for system prompt.
     * Token budget indicator: "520 / 800 Tokens (Safe Range)".
     * Config for Max Sentences (5) & Max Words (100).
   - VieNeu v3 Turbo TTS Engine:
     * Dropdowns for Voice Speaker ("Đoan Trang", "Anh Thư", "Minh Quân") and Style Mode ("tu_nhien", "doc_truyen", "tin_tuc").
     * Button: [▶️ Test Voice Sample].
   - Knowledge Base & Active Sessions:
     * Compact table of YAML files (`general_info.yaml`, `schedules_deadlines.yaml`) with [Edit] buttons.
     * Active WebRTC Connections table (Session ID, Transport type e.g. "TURN TLS :443", and [Disconnect] button).

DELIVERABLE:
Write clean, modular, production-ready code (HTML/CSS/JS or React Component) that implements all the functional logic (preset switching, ping test simulation, token counting) with precision and high visual polish.
```

---

## 💻 4. MÃ NGUỒN HTML/CSS/JS DASHBOARD HOÀN CHỈNH (STANDALONE RUNNABLE CODE)

File mã nguồn dưới đây có thể lưu thành `dashboard.html` và chạy trực tiếp trên bất kỳ trình duyệt nào:

```html
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Robot AI Host — LLM & Control Workbench</title>
    <style>
        :root {
            --bg-dark: #0b0f19;
            --card-bg: rgba(15, 23, 42, 0.85);
            --card-border: #1e293b;
            --accent-blue: #38bdf8;
            --accent-indigo: #6366f1;
            --accent-green: #34d399;
            --accent-purple: #c084fc;
            --accent-amber: #fbbf24;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-main);
            padding: 12px;
            font-size: 12px;
        }

        /* Top Bar */
        .header {
            background: linear-gradient(90deg, #1e1b4b 0%, #0f172a 100%);
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 10px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.4);
        }
        .logo-box { display: flex; align-items: center; gap: 10px; }
        .logo-title { font-size: 16px; font-weight: 800; color: var(--accent-blue); letter-spacing: -0.5px; }
        .badge { padding: 3px 8px; border-radius: 12px; font-size: 10px; font-weight: 700; text-transform: uppercase; }
        .badge-green { background: rgba(52, 211, 153, 0.15); color: var(--accent-green); border: 1px solid #059669; }
        .badge-purple { background: rgba(192, 132, 252, 0.15); color: var(--accent-purple); border: 1px solid #7e22ce; }

        /* KPI Strip */
        .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 12px; }
        .kpi-card {
            background: var(--card-bg); border: 1px solid var(--card-border);
            border-radius: 6px; padding: 10px 12px;
        }
        .kpi-title { font-size: 10px; color: var(--text-muted); font-weight: bold; text-transform: uppercase; }
        .kpi-val { font-size: 18px; font-weight: 800; color: var(--accent-blue); margin: 2px 0; }
        .kpi-sub { font-size: 10px; color: var(--text-muted); }

        /* Main Grid (Dual Column Layout) */
        .main-grid { display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 12px; }

        /* Cards */
        .card {
            background: var(--card-bg); border: 1px solid var(--card-border);
            border-radius: 8px; padding: 12px; margin-bottom: 12px;
            backdrop-filter: blur(8px);
        }
        .card-header {
            font-size: 12px; font-weight: 700; color: #f1f5f9;
            margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid #1e293b;
            display: flex; justify-content: space-between; align-items: center;
        }
        .card-header .tag { font-size: 10px; color: var(--accent-blue); font-weight: normal; }

        /* Forms */
        .form-group { margin-bottom: 8px; }
        label { display: block; font-size: 10px; color: var(--text-muted); margin-bottom: 3px; font-weight: 600; }
        input[type="text"], select, textarea {
            width: 100%; background: #020617; border: 1px solid #334155; border-radius: 5px;
            color: var(--text-main); padding: 6px 8px; font-size: 11px; font-family: inherit;
        }
        input[type="text"]:focus, select:focus, textarea:focus { border-color: var(--accent-blue); outline: none; }

        .btn {
            padding: 6px 12px; border-radius: 5px; font-size: 11px; font-weight: 700; cursor: pointer; border: none; transition: 0.2s;
        }
        .btn-primary { background: #4f46e5; color: white; }
        .btn-primary:hover { background: #4338ca; }
        .btn-success { background: #059669; color: white; }
        .btn-success:hover { background: #047857; }
        .btn-secondary { background: #334155; color: #e2e8f0; }

        /* LLM Tester Playground Box */
        .tester-box {
            background: #020617; border: 1px solid var(--accent-indigo);
            border-radius: 6px; padding: 10px;
        }
        .test-chat-log {
            background: #080d1a; border: 1px solid #1e293b; border-radius: 5px;
            padding: 8px; height: 110px; overflow-y: auto; font-size: 11px; margin-bottom: 8px;
        }
        .msg-user { color: var(--accent-blue); font-weight: bold; margin-bottom: 4px; }
        .msg-bot { color: var(--accent-green); line-height: 1.4; }
        .test-metrics {
            font-size: 10px; color: var(--text-muted); display: flex; justify-content: space-between;
            border-top: 1px dashed #1e293b; padding-top: 6px; margin-bottom: 8px;
        }

        /* Tables */
        table { width: 100%; border-collapse: collapse; font-size: 11px; }
        th, td { padding: 6px; border-bottom: 1px solid #1e293b; text-align: left; }
        th { background: #0f172a; color: var(--text-muted); font-weight: 700; }
    </style>
</head>
<body>

    <!-- TOP HEADER BAR -->
    <div class="header">
        <div class="logo-box">
            <span class="logo-title">🤖 ROBOT AI HOST — LLM & CONTROL WORKBENCH</span>
            <span class="badge badge-green">ONLINE v0.1.0</span>
            <span class="badge badge-purple">Apple M1 (8GB)</span>
        </div>
        <div>
            <span style="font-size: 11px; color: var(--text-muted); margin-right: 12px;">
                Profile: <strong style="color:var(--accent-blue);">hybrid_local_vi</strong> | Sessions: <strong style="color:var(--accent-green);">2 / 4</strong>
            </span>
            <button class="btn btn-primary" onclick="alert('Đã áp dụng cấu hình LLM mới vào hệ thống!')">💾 Lưu Cấu Hình</button>
            <button class="btn btn-secondary" onclick="confirm('Khởi động lại FastAPI Server?') && alert('Server đang khởi động lại...')">⚡ Restart</button>
        </div>
    </div>

    <!-- ESSENTIAL SYSTEM KPI STRIP -->
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-title">Phần Cứng Apple M1</div>
            <div class="kpi-val">28% <span style="font-size:11px; font-weight:normal; color:var(--accent-purple);">| 5.2GB RAM</span></div>
            <div class="kpi-sub">Sức chứa: Max 4 Sessions đồng thời</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Độ Trễ Phản Hồi (P95)</div>
            <div class="kpi-val" style="color:var(--accent-green);">1,240 ms</div>
            <div class="kpi-sub">VAD Stop ➔ First Audio (Mục tiêu ≤ 1.6s)</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Mô Hình LLM Hiện Tại</div>
            <div class="kpi-val" style="color:var(--accent-purple);">Gemini 2.5 Flash Lite</div>
            <div class="kpi-sub">AGY Endpoint (:20128) | TTFB: 380ms</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Trí Thức & An Toàn</div>
            <div class="kpi-val" style="color:var(--accent-blue);">100% Grounded</div>
            <div class="kpi-sub">4 File YAML | 0 Cảnh báo Vi phạm</div>
        </div>
    </div>

    <!-- DUAL COLUMN WORKBENCH -->
    <div class="main-grid">
        <!-- LEFT COLUMN: DEDICATED LLM WORKBENCH (CONFIG + TESTER) -->
        <div>
            <!-- LLM CONFIGURATION CARD -->
            <div class="card">
                <div class="card-header">
                    ⚙️ Cấu Hình Mô Hình Ngôn Ngữ (LLM Model Settings)
                    <span class="tag">API: PUT /v1/admin/settings</span>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                    <div class="form-group">
                        <label>Chọn Preset Nhanh:</label>
                        <select id="presetSelect" onchange="applyPreset(this.value)">
                            <option value="gemini-flash-lite" selected>Gemini 2.5 Flash Lite (AGY Local Endpoint)</option>
                            <option value="gemini-flash-direct">Gemini 1.5 Flash (Direct Google API)</option>
                            <option value="llama3-local">Llama 3 8B Instruct (Local Ollama / vLLM)</option>
                            <option value="custom">Custom OpenAI-Compatible API</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Tên Model ID (LLM_MODEL):</label>
                        <input type="text" id="llmModel" value="agy/gemini-2.5-flash-lite" />
                    </div>
                </div>

                <div class="form-group">
                    <label>Base URL Endpoint (LLM_BASE_URL):</label>
                    <input type="text" id="llmBaseUrl" value="http://127.0.0.1:20128/v1" />
                </div>

                <div style="display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 8px;">
                    <div class="form-group">
                        <label>API Key (LLM_API_KEY):</label>
                        <input type="text" id="llmApiKey" value="sk-agy-**************************" />
                    </div>
                    <div class="form-group">
                        <label>Timeout (LLM_TIMEOUT_SECONDS):</label>
                        <input type="text" value="30s (Retry: ON)" />
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px;">
                    <div class="form-group">
                        <label>Temperature (0.0 - 1.0):</label>
                        <input type="text" id="llmTemp" value="0.5" />
                    </div>
                    <div class="form-group">
                        <label>Max Output Tokens:</label>
                        <input type="text" value="100 (Ngắn gọn)" />
                    </div>
                    <div class="form-group">
                        <label>Streaming Mode:</label>
                        <select><option selected>ENABLED (True)</option><option>DISABLED (False)</option></select>
                    </div>
                </div>
            </div>

            <!-- INSTANT LLM TESTER PLAYGROUND -->
            <div class="card">
                <div class="card-header">
                    🧪 Kiểm Thử Mô Hình Tức Thời (Instant LLM Test Playground)
                    <span class="tag">Kiểm tra kết nối & Phản hồi trước khi Save</span>
                </div>

                <div class="tester-box">
                    <div class="test-chat-log" id="testChatLog">
                        <div class="msg-user">👤 User: Lịch nghỉ hè năm nay của trường bắt đầu khi nào vậy?</div>
                        <div class="msg-bot" id="botResponse">🤖 Mây Mây (LLM Output): Dạ, theo kế hoạch nhà trường, lịch nghỉ hè bắt đầu từ ngày 01/06 nè! Bạn cần tra cứu thêm thông tin lớp nào không nha?</div>
                    </div>

                    <div class="test-metrics">
                        <span>⏱️ TTFB: <strong style="color:var(--accent-green);" id="metricTtfb">380 ms</strong></span>
                        <span>⚡ Tốc độ: <strong style="color:var(--accent-blue);" id="metricSpeed">42 tokens/s</strong></span>
                        <span>📊 Tokens: <strong id="metricTokens">48 in / 32 out</strong></span>
                        <span>✅ Status: <strong style="color:var(--accent-green);">200 OK</strong></span>
                    </div>

                    <div style="display: flex; gap: 8px;">
                        <input type="text" id="testQuery" placeholder="Nhập câu hỏi test mô hình LLM..." value="Trường mình có câu lạc bộ AI không mây mây?" />
                        <button class="btn btn-success" onclick="runLlmTest()">[🚀 Run Test Model]</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- RIGHT COLUMN: PERSONA, VOICE, KNOWLEDGE BASE -->
        <div>
            <!-- PERSONA & PROMPT -->
            <div class="card">
                <div class="card-header">🤖 System Prompt Mây Mây <span class="tag">config/assistant_school.yaml</span></div>
                <div class="form-group">
                    <textarea rows="3">Bạn là Mây Mây, trợ lý AI giọng nói tiếng Việt của Trường. Bạn giao tiếp tự nhiên, thân thiện. Trả lời ngắn gọn từ 1-2 câu. Dùng thán từ 'Dạ/À/nè/nha'. Không bịa đặt thông tin trường học.</textarea>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--text-muted);">
                    <span>Tên Persona: <strong>Mây Mây</strong> | Xưng hô: <strong>mình - bạn</strong></span>
                    <span>Budget: <strong style="color:var(--accent-green);">520 / 800 Tokens</strong></span>
                </div>
            </div>

            <!-- TTS VOICE ENGINE -->
            <div class="card">
                <div class="card-header">🔊 Giọng Nói VieNeu v3 Turbo (ONNX) <span class="tag">Local TTS</span></div>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px;">
                    <div class="form-group">
                        <label>Voice Speaker:</label>
                        <select><option selected>Đoan Trang</option><option>Anh Thư</option><option>Minh Quân</option></select>
                    </div>
                    <div class="form-group">
                        <label>Style Mode:</label>
                        <select><option selected>tu_nhien</option><option>doc_truyen</option><option>tin_tuc</option></select>
                    </div>
                    <div class="form-group">
                        <label>Tốc độ:</label>
                        <input type="text" value="1.0x" />
                    </div>
                </div>
                <div style="text-align: right; margin-top: 4px;">
                    <button class="btn btn-secondary" onclick="alert('🔊 Nghe thử: Dạ, Mây Mây chào bạn nè!')">▶️ Nghe Thử Giọng</button>
                </div>
            </div>

            <!-- KNOWLEDGE BASE & ACTIVE SESSIONS -->
            <div class="card">
                <div class="card-header">📚 Dữ Liệu Trường Học & WebRTC Sessions <span class="tag">knowledge/school/</span></div>
                <table>
                    <thead>
                        <tr>
                            <th>Tập tin Tri Thức</th>
                            <th>Dung Lượng</th>
                            <th>Trạng Thái</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><code>general_info.yaml</code></td>
                            <td>12.4 KB</td>
                            <td><span style="color:var(--accent-green);">Active</span></td>
                        </tr>
                        <tr>
                            <td><code>schedules_deadlines.yaml</code></td>
                            <td>45.1 KB</td>
                            <td><span style="color:var(--accent-green);">Active</span></td>
                        </tr>
                    </tbody>
                </table>

                <div style="margin-top: 8px; font-weight: bold; color: var(--text-muted); font-size: 10px; margin-bottom: 4px;">Phiên Đang Kết Nối (2/4 Active):</div>
                <table>
                    <tbody>
                        <tr>
                            <td><code>sess_8f92a10</code> (Mobile Browser)</td>
                            <td>TURN TLS :443</td>
                            <td><button class="btn btn-secondary" style="color:#ef4444;" onclick="alert('Ngắt phiên')">Ngắt</button></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        // JS logic đổi Preset LLM
        function applyPreset(val) {
            const modelInput = document.getElementById('llmModel');
            const urlInput = document.getElementById('llmBaseUrl');
            const keyInput = document.getElementById('llmApiKey');

            if (val === 'gemini-flash-lite') {
                modelInput.value = 'agy/gemini-2.5-flash-lite';
                urlInput.value = 'http://127.0.0.1:20128/v1';
                keyInput.value = 'sk-agy-**************************';
            } else if (val === 'gemini-flash-direct') {
                modelInput.value = 'gemini-1.5-flash';
                urlInput.value = 'https://generativelanguage.googleapis.com/v1beta/openai/';
                keyInput.value = 'AIzaSy**************************';
            } else if (val === 'llama3-local') {
                modelInput.value = 'llama3:8b-instruct';
                urlInput.value = 'http://127.0.0.1:11434/v1';
                keyInput.value = 'ollama-local-key';
            }
        }

        // JS logic Test LLM Model
        function runLlmTest() {
            const query = document.getElementById('testQuery').value;
            const model = document.getElementById('llmModel').value;
            const log = document.getElementById('testChatLog');
            
            document.getElementById('metricTtfb').innerText = 'Đang gọi...';
            
            setTimeout(() => {
                const randomTtfb = Math.floor(Math.random() * 80) + 320;
                document.getElementById('metricTtfb').innerText = randomTtfb + ' ms';
                document.getElementById('metricSpeed').innerText = '45 tokens/s';
                document.getElementById('metricTokens').innerText = '35 in / 28 out';

                const newMsg = `
                    <div style="margin-top:8px; border-top:1px solid #1e293b; padding-top:6px;">
                        <div class="msg-user">👤 User: ${query}</div>
                        <div class="msg-bot">🤖 Mây Mây (${model}): Dạ, câu hỏi của bạn đã được kiểm thử thành công qua mô hình ${model}! Câu trả lời chuẩn xác và tuân thủ định dạng ngắn gọn nha.</div>
                    </div>
                `;
                log.innerHTML += newMsg;
                log.scrollTop = log.scrollHeight;
            }, 400);
        }
    </script>
</body>
</html>
```
