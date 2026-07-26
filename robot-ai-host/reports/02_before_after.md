# BEFORE–AFTER REPORT — Robot AI Host v0.2.0

## I. BỐN VẤN ĐỀ ĐÃ SỬA

| # | Vấn đề | Nguyên nhân | File đã sửa | Test | Trạng thái |
|---|--------|------------|-------------|------|-----------|
| 1 | Chỉ chạy CPU trên Mac | Không có PyTorch MPS detection | `app/core/device_manager.py` (mới) | `check_acceleration.py` → MPS PASS | ✅ |
| 2 | Không có nơi thống nhất cấu hình LLM | Settings rải rác, không có UI | `app/config.py` + `/settings` page | `/api/system/devices` → 200 OK | ✅ |
| 3 | Câu trả lời dài, lan man, lặp | Không có max_tokens, system prompt yếu | `pipeline_factory.py` + `app/core/system_prompt.py` | temperature=0.2, max_tokens=160 | ✅ |
| 4 | Sai persona (Antigravity/programmer) | Model tự nhận danh tính, prompt không cấm | `config/assistant_school.yaml` + system prompt mới | Prohibited claims list | ✅ |

## II. CÁC VẤN ĐỀ BỔ SUNG ĐÃ SỬA

| # | Vấn đề | Nguyên nhân | File đã sửa | Trạng thái |
|---|--------|------------|-------------|-----------|
| 5 | Mỗi câu xuất hiện 2 lần | TextFrame đi qua cả TTS và assistant aggregator | `app/processors/stream_deduplicator.py` (mới) | ✅ |
| 6 | STT ghi nhận tiếng loa/video | Không có echo gate, min speech, duplicate check | `app/processors/stt_guard.py` (mới) | ✅ |
| 7 | Partial STT gửi tới LLM | InterimTranscriptionFrame không bị lọc | STTGuard.final_only=True | ✅ |
| 8 | Không có device diagnostic | Không có endpoint kiểm tra MPS/MLX | `/api/system/devices` | ✅ |

## III. THÀNH PHẦN CHẠY Ở ĐÂU

| Thành phần | Backend | Device |
|-----------|---------|--------|
| STT | MLX (Whisper large-v3-turbo) | **Apple GPU (MPS)** |
| LLM | `agy/gemini-3.1-flash-lite` qua gateway | **Remote** (127.0.0.1:20128) |
| TTS | Piper HTTP (ONNX) | **CPU** (ONNX không hỗ trợ Metal) |
| Pipecat host | Python asyncio | **CPU orchestration** |

## IV. FILE MỚI

| File | Mục đích |
|------|----------|
| `app/core/device_manager.py` | Phát hiện MPS/MLX/CUDA/CPU |
| `app/core/system_prompt.py` | Build system prompt từ YAML |
| `app/processors/stt_guard.py` | Lọc STT: chống nhiễu, echo, duplicate |
| `app/processors/stream_deduplicator.py` | Chống phát câu 2 lần |
| `config/assistant_school.yaml` | Profile trợ lý nhà trường |
| `scripts/check_acceleration.py` | Kiểm tra MPS/MLX bằng inference thật |
| `knowledge/README.md` | Thư mục dữ liệu nhà trường |

## V. FILE ĐÃ SỬA

| File | Thay đổi |
|------|----------|
| `app/config.py` | Thêm llm_temperature, llm_max_tokens, device_policy, assistant_profile |
| `app/pipecat_runtime/pipeline_factory.py` | System prompt mới, STT guard, deduplicator, max_tokens, temperature |
| `app/main.py` | Thêm `/api/system/devices` + `/settings` page |

## VI. TEST RESULTS

```
pytest:  90/90 passed ✅
frontend: 4/4 passed ✅
MPS:     MPS matmul 100x100: 85ms ✅
MLX:     MLX matmul 100x100: 20ms ✅
Devices: {"pytorch_device":"mps","stt_backend":"mlx"} ✅
Health:  {"status":"ok"} ✅
```

## VII. CÁC URL MỚI

| URL | Mô tả |
|-----|-------|
| `http://127.0.0.1:8000/settings` | Trang cấu hình LLM + assistant |
| `http://127.0.0.1:8000/api/system/devices` | Device diagnostic JSON |
| `http://127.0.0.1:8000/client/` | Trang client (đã có) |

## VIII. LỆNH CHẠY

```bash
# Kiểm tra acceleration
PYTHONPATH= .venv-hybrid/bin/python scripts/check_acceleration.py

# Start Piper (terminal 1)
PYTHONPATH= .venv-piper/bin/python -m piper.http_server \
  --host 127.0.0.1 --port 5000 --data-dir models/piper \
  -m vi_VN-vais1000-medium

# Start host (terminal 2)
PYTHONPATH= .venv-hybrid/bin/python -m app.main --profile hybrid_local_vi

# Mở client
open http://127.0.0.1:8000/client/

# Cấu hình
open http://127.0.0.1:8000/settings
```
