# Manual Microphone Acceptance — macOS

## Điều kiện

- Python 3.12 và dependencies đã cài.
- Browser frontend đã build.
- `.env` có Google credential, OpenAI key, model và verified `vi-VN` Chirp3-HD/Journey voice.
- Dùng `http://127.0.0.1:8000/client` trên cùng máy; LAN cần HTTPS.

## Khởi động

```bash
uv run python scripts/check_cloud_profile.py --profile google_vi
uv run python -m app.main --profile google_vi
```

## Kịch bản bắt buộc

| Bước | Thao tác | Tiêu chí |
|---|---|---|
| 1 | Mở client, chọn mic, Connect | transport `ready`, bot ready |
| 2 | Nói “Tên tôi là Minh Hiếu.” | final transcript chứa đúng tên hoặc sai số được ghi lại |
| 3 | Chờ phản hồi | nội dung liên quan tới câu vừa nói |
| 4 | Nghe loa | giọng Việt thật, không tone |
| 5 | Khi bot đang nói, nói “Dừng lại.” | audio cũ dừng và không phát lại |
| 6 | Hỏi “Tôi vừa nói tên gì?” | bot trả lời Minh Hiếu |
| 7 | Mở `/v1/metrics` | không rỗng, có runtime metrics |
| 8 | Lặp 30 lượt | không crash/reconnect bất thường |

## Evidence cần lưu

- `artifacts/runtime-metrics.jsonl`
- output `report_latency.py`
- browser log export/screenshot
- server log
- voice/profile/model/region đã dùng
- PASS/FAIL cho từng bước

## Không được ghi PASS khi

- dùng profile mock;
- chỉ nghe tone;
- transcript là scripted;
- chỉ bấm nút “Dừng loa cục bộ (debug)” thay cho nói chen;
- chưa kiểm tra audio stale/context sau interruption.
