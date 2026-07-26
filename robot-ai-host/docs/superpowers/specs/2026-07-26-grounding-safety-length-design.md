# Grounding + Safety + Length enforcement — Design (Phương án A)

Ngày: 2026-07-26. User duyệt chat ("a"). Phạm vi: 3 lỗi nặng + bộ test.

## 1. Chống bịa — context-injection (RAG-lite)

Processor mới `TurnGroundingProcessor` (app/processors/turn_grounding.py), đặt cạnh
ContextCompactor (sau user aggregator, trước LLM). Trên mỗi `LLMContextFrame`:

- Lấy message user cuối làm query → `KnowledgeStore.search()` (đã có, keyword-score).
- Có hit → gỡ note cũ rồi append system message `[DỮ LIỆU NHÀ TRƯỜNG] ...` gồm
  evidence + nguồn/version/ngày + cảnh báo hết hạn. LLM buộc trả lời theo đó, kèm nguồn.
- Không hit NHƯNG query chứa từ khóa trường học (học phí, lịch, hạn, phòng, thủ tục,
  liên hệ, biểu mẫu...) → append `[DỮ LIỆU NHÀ TRƯỜNG] KHÔNG có tài liệu` — buộc nói
  "chưa có thông tin", cấm đoán.
- Small talk (không từ khóa) → không inject gì.
- Note của lượt trước luôn bị gỡ trước khi append (tránh phình context).

Knowledge dùng 4 YAML placeholder sẵn có (`knowledge/school/`), bổ sung ~6-8 entry
mẫu Đại Nam (học phí, wifi, ký túc xá, xe buýt...) — tất cả giữ chữ "placeholder"
trong title, trường thay bằng dữ liệu thật sau.

## 2. An toàn trẻ em — cùng processor

Cùng `TurnGroundingProcessor`, quét query bằng bộ từ khóa nguy cơ (tự tử/tự hại/
muốn chết/bắt nạt/đánh/bạo lực/xâm hại/đe dọa...):

- Hit → append system note `[AN TOÀN]`: phản hồi đồng cảm, khuyên tìm ngay thầy cô/
  tư vấn học đường/người thân; không phán xét, không tự xử lý thay chuyên gia.
- Ghi `artifacts/safety_alerts.jsonl`: timestamp, session/context id, trích đoạn
  (100 ký tự), keyword khớp. KHÔNG tự gửi đi đâu — nhà trường tự xem file.

## 3. Length enforcement — sửa root cause

`ResponsePolicyProcessor` hiện đếm trên từng TextFrame delta → không bao giờ cắt.
Sửa: đếm TÍCH LŨY theo lượt — reset ở `LLMFullResponseStartFrame`, cộng dồn câu/từ
qua các TextFrame, vượt trần → nuốt các TextFrame còn lại tới `LLMFullResponseEndFrame`.
Trần nâng thành trần cứng chống tràn: 8 câu / 150 từ (config + yaml); độ ngắn
thường ngày do prompt điều khiển (đã có).

## 4. Tests

- `test_turn_grounding.py`: hit → note nguồn; câu hỏi trường không data → note KHÔNG;
  small talk → không note; note cũ bị gỡ; safety keyword → note + jsonl ghi đúng.
- `test_response_policy.py`: stream delta giả lập vượt 8 câu → frame sau bị nuốt,
  end frame reset; dưới trần → nguyên vẹn.
- Soak script `scripts/soak_stream_tts.py` (chạy tay): render streaming liên tục
  N phút, in RTF + RSS; phát hiện kẹt lock/leak.

## Không làm đợt này

Function-calling LLM (chờ xác minh proxy), semantic retrieval, webhook báo động,
auth API, gộp đường two-tier.
