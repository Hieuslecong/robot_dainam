# Expressive TTS (Phương án A) — Design

Ngày: 2026-07-26. Trạng thái: user đã duyệt (chat).

## Mục tiêu
Giọng VieNeu cảm xúc hơn, không đổi model, không chậm thêm. Ưu tiên "cân bằng".

## Phát hiện nền tảng
- VieNeu v3 Turbo chỉ có 3 style thật: `tu_nhien`, `tin_tuc`, `doc_truyen` (style lạ → tu_nhien). STYLE_MAP cũ dùng `vui`/`buon` — không tồn tại.
- 14 giọng preset có tên (default Phạm Tuyên); chọn giọng nữ trẻ sôi nổi.
- Emotion tag inline được train sẵn: `[cười]`, `[thở dài]`, `[hắng giọng]` → tiếng thật.

## Thay đổi
1. `vieneu_engine.py`: STYLE_MAP → {cheerful,encouraging: doc_truyen; serious: tin_tuc; còn lại: tu_nhien}; `infer(..., voice=env VIENEU_VOICE)`; voice sai → log + fallback default.
2. `config.py`: `vieneu_voice` (env `VIENEU_VOICE`).
3. `pipeline_factory.py`: truyền style vào `synthesize` (style theo turn, default friendly).
4. Text filter: GIỮ 3 emotion tag qua VieNeu; strip tag trước Piper (Piper đọc thành chữ).
5. Persona prompt: văn biểu cảm (thán từ, câu cảm, nhịp ngắn dài) + emotion tag tiết chế (~1 tag/vài lượt).
6. Script render mẫu giọng nữ → `artifacts/upgrade/voice_samples/*.wav` → user nghe chốt `VIENEU_VOICE`.

## Fallback
- Voice không tồn tại → default preset.
- Style lạ → tu_nhien (SDK có sẵn).
- Tag sang Piper → strip regex.

## Test
Unit: STYLE_MAP hợp lệ, filter giữ tag, Piper path strip tag, voice env wire. Nghiệm thu: nghe wav mẫu + live.
