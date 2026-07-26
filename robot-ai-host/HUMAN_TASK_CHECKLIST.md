# HUMAN_TASK_CHECKLIST

Mọi việc bắt buộc cần con người thật. Mỗi mục: mô tả → cách làm → tiêu chí đạt → gate đang chờ.
Cập nhật sau mỗi phase. Trạng thái: ☐ chưa làm / ☑ xong.

## Khẩn cấp trước khi tiếp tục

### ☑ 0. Giải phóng dung lượng đĩa — XONG (2026-07-26, 34GB trống; model đã tải, benchmark đã chạy)

## Phase 0

### ☐ 1. Soak test 30 phút (gate Phase 0, mục 12.4)
- **Mô tả:** hội thoại thật 30 phút qua browser client, profile `hybrid_local_vi`.
- **Cách làm:**
  1. `scripts/run_piper.sh` (terminal 1), server (terminal 2), `npm run dev --prefix clients/browser` (terminal 3).
  2. Nói chuyện ≥30 turn; ≥10 lần ngắt lời khi bot đang nói; ≥5 lần reload trang (reconnect); tắt LLM endpoint ≥3 lần giữa chừng; kill Piper ≥3 lần.
  3. Theo dõi: RAM server (Activity Monitor), `artifacts/runtime-metrics.jsonl` (đủ event `turn_timeline`), không audio cũ phát lại sau reconnect.
- **Tiêu chí đạt:** không context growth mất kiểm soát (log `context_compacted` xuất hiện sau ~8 turn), không stale audio, metrics đủ timeline, không orphan process.
- **Gate chờ:** Phase 0 PASS đầy đủ (hiện PARTIAL).

### ☐ 2. Xác nhận tên persona với nhà trường (spec 9.4)
- **Mô tả:** tên "N.E.K.O" là quyết định branding, chưa được xác nhận.
- **Cách làm:** hỏi đại diện trường; sau xác nhận đặt `PERSONA_NAME=<tên>` trong `.env`.
- **Tiêu chí đạt:** email/văn bản xác nhận + `.env` cập nhật.
- **Gate chờ:** persona acceptance (mục 24.4).

### ☐ 3. Nghe thử persona mới qua mic thật (mục 12.3, vòng sơ bộ)
- **Mô tả:** kiểm tra văn phong mình–bạn, không boilerplate.
- **Cách làm:** chạy stack như mục 1, hỏi các câu bắt buộc:
  - "Bạn là ai?" · "Tên tôi là Minh Hiếu." · "Tôi vừa nói tên gì?" · "Dừng lại."
- **Tiêu chí đạt:** trả lời xưng "mình", không "sẵn sàng hỗ trợ", nhớ tên trong phiên, dừng khi yêu cầu; user transcript không lọt vào TTS.
- **Gate chờ:** LOCAL_MIC_ACCEPTANCE.md.

## Phase 1 (chuẩn bị trước)

### ☐ 4. Thu corpus STT vòng 2 (spec 23.1)
- **Mô tả:** 200–300 câu tự thu, có ground truth.
- **Cách làm:** tối thiểu 6 người (2 Bắc, 2 Trung, 2 Nam; cân bằng nam/nữ); script câu gồm: tên riêng, mã sinh viên, ngày giờ, phòng/khoa, thuật ngữ trường, Việt–Anh, câu ngắn/dài, nhanh/chậm; thu cả mẫu noise/echo/silence; ghi 16kHz+ WAV; điền `benchmarks/stt/manifest.jsonl` (schema sẽ tạo ở Phase 1).
- **Tiêu chí đạt:** ≥200 utterance có transcript chuẩn, phủ đủ category.
- **Gate chờ:** chốt STT mặc định (gate 8.6) — vòng 1 corpus công khai chỉ xếp hạng sơ bộ.

### ☐ 5. Panel người nghe TTS ≥8 người (spec 23.2a)
- **Mô tả:** chấm naturalness/emotion/preference — máy không tự chấm được.
- **Cách làm:** ≥8 người Việt bản ngữ ngoài nhóm dev; blind A/B (Piper vs VieNeu light vs VieNeu expressive vs cấu hình hai tầng); mỗi người chấm đủ 80 câu, MOS 1–5; lưu raw từng người từng câu vào `artifacts/upgrade/tts-panel-raw.csv`.
- **Tiêu chí đạt:** naturalness ≥4.2/5, preference over Piper ≥80%, emotion ≥85%.
- **Gate chờ:** TTS gate 16.6 (Phase 2) — đến khi có panel: BLOCKED.

### ☐ 6b. Nghe thẩm định VieNeu smoke (mới — Phase 1)
- **Mô tả:** máy đã sinh `artifacts/upgrade/vieneu_smoke.wav` (VieNeu v3 Turbo). Máy KHÔNG tự chấm được chất lượng giọng.
- **Cách làm:** nghe file; nếu chấp nhận được → bật `TTS_TWO_TIER_ENABLED=true` trong `.env` và nghe lại qua browser client.
- **Tiêu chí đạt:** quyết định bật/tắt two-tier có căn cứ nghe thật; panel ≥8 người (mục 5) vẫn là gate chính thức.
- **Gate chờ:** TTS gate 16.6.

### ☐ 7. Nội dung knowledge thật (Phase 2)
- **Mô tả:** `knowledge/school/*.yaml` hiện là placeholder có metadata đúng schema.
- **Cách làm:** thay bằng tài liệu thật của trường (điền source_id/version/effective_date/issuing_unit thật), giữ nguyên schema.
- **Tiêu chí đạt:** tra cứu trả thông tin thật, có nguồn thật.
- **Gate chờ:** acceptance mục 5 (read-only tools có nguồn).

### ☐ 8. Live agent eval (Phase 2/3)
- **Mô tả:** gate "correct tool ≥95%" và "zero unauthorized/false success end-to-end" cần LLM endpoint thật + phiên thoại thật.
- **Cách làm:** bật server với LLM gateway thật, chạy bộ câu eval 23.3 (intent/risk/tool/confirmation), ghi kết quả vào artifacts.
- **Tiêu chí đạt:** ≥95% đúng tool trên bộ eval; 0 hành động không xác nhận.
- **Gate chờ:** gate Phase 2 + Phase 3 phần runtime.

### ☐ 6. Legal review license/voice (mục 21)
- **Mô tả:** xác minh các mục NOT VERIFIED trong LICENSE_INVENTORY.md trước phân phối.
- **Cách làm:** đọc license gốc từng model/voice; ghi kết luận vào LICENSE_INVENTORY.md (chuyển REPORTED → VERIFIED).
- **Tiêu chí đạt:** không còn NOT VERIFIED cho thành phần được phân phối.
- **Gate chờ:** phân phối thương mại.
