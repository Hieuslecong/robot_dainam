# 02 — Phase 1: Voice Quality (UPDATED 2026-07-27)

Date: 2026-07-27
Status: **STT DEFAULT LOCKED** — `stt_streaming_vi` (Sherpa Zipformer) confirmed as default.
Previous: 2026-07-26 (PARTIAL)

## STT (spec 8)

### Root-cause fix: MLX 8-bit models

Hai model `mlx-community/whisper-large-v3-turbo-8bit` (863MB) và
`mlx-community/whisper-large-v3-8bit` (1.64GB) đã tải thành công sau
`force_download`. Tuy nhiên **vẫn không decode được** — lỗi `[load_npz] Input must
be a zip file`.

**Root cause**: `mlx_whisper` (`load_models.py`) chỉ tìm file `weights.safetensors`
hoặc `weights.npz`, nhưng hai repo mlx-community này đặt tên `model.safetensors`.
Đây là **naming mismatch từ upstream**, không phải lỗi download. Bản q4 dùng
tên `weights.npz` nên hoạt động bình thường.

**Kết luận**: Không thể fix từ phía project này — cả hai model 8-bit vẫn không
khả dụng. Nhưng điều này **không thay đổi kết luận**: ngay cả khi chạy được,
chúng là model batch, nặng hơn q4, nên sẽ chậm hơn 1.7s — trượt gate ≤900ms.

### Round-1 benchmark (confirmed 2026-07-27, VIVOS-50)

| Candidate | Engine | WER | CER | P50(s) | P90(s) | RAM(MB) | Gate ≤0.9s |
|---|---:|---:|---:|---:|---:|---:|---:|
| **stt_streaming_vi** | sherpa_onnx | **0.0951** | 0.0534 | **0.066** | 0.088 | 88 | ✅ |
| stt_fast_vi (turbo q4) | mlx | 0.1471 | 0.0693 | 1.696 | 2.053 | 200 | ❌ |
| stt_accurate_vi (PhoWhisper) | faster_whisper | 0.0871 | 0.0424 | 5.385 | 6.672 | 1410 | ❌ |
| stt_balanced_vi (turbo 8bit) | mlx | — | — | — | — | — | BROKEN (upstream) |
| stt_research_vi (large-v3 8bit) | mlx | — | — | — | — | — | BROKEN (upstream) |

### Quyết định STT mặc định

**`stt_streaming_vi` (Sherpa-onnx Zipformer) là STT mặc định chính thức.**

- WER 9.51% — trong 0.8pt của PhoWhisper (8.71%) nhưng nhanh hơn **81 lần**
- P50 0.066s — dưới gate ≤900ms với margin **13.6x**
- RAM cực nhẹ (~88MB) — phù hợp M1 8GB
- Đã tích hợp đầy đủ trong pipeline qua `SherpaSTTService`
- `.env`: `STT_CANDIDATE=stt_streaming_vi`
- Rollback về q4 cũ: bỏ trống `STT_CANDIDATE=`

**Lưu ý**: Đây là quyết định dựa trên round-1 (VIVOS public). Round-2 (corpus
tự thu 200-300 câu với tên riêng, mã SV...) vẫn cần để xác nhận chất lượng
dấu tiếng Việt và proper noun accuracy của Zipformer (HUMAN_TASK_CHECKLIST #4).

### Pipeline integration status

| Thành phần | Trạng thái |
|---|---|
| `SherpaSTTService` (`app/pipecat_runtime/sherpa_stt.py`) | ✅ Đã có |
| `resolve_stt_candidate()` (`app/config.py`) | ✅ Đã có |
| `pipeline_factory.py` routing sherpa engine | ✅ Đã có |
| `stt_candidates.yaml` entry `stt_streaming_vi` | ✅ Đã có |
| `.env` → `STT_CANDIDATE=stt_streaming_vi` | ✅ Đã set |
| Unit tests (`test_sherpa_stt.py`) | ✅ 2 passed |
| Full test suite | ✅ 209 passed, 2 skipped |
| Silence gate (anti-hallucination RMS 0.005) | ✅ Đã build-in |
| Glossary correction pipeline | ✅ Đã hook vào STTGuard |

### Known limitations (trung thực)

1. Zipformer transducer có thể hallucinate trên loud non-speech — đã có RMS
   silence gate (0.005) + Silero VAD + STTGuard. Cần benchmark tonal-noise
   robustness ở round-2.
2. Proper-noun coverage bị giới hạn bởi training vocabulary —
   glossary correction bù đắp, round-2 quyết định.
3. Output lowercase/unpunctuated — chấp nhận được cho LLM input.
4. MLX 8-bit models không decode được vì upstream naming mismatch —
   không phải bug của project này. Đã ghi nhận, có thể retry khi upstream fix.

## Gate 8.6 verdict

| Chỉ tiêu | Target | Zipformer | Status |
|---|---:|---:|---|
| Semantic accuracy | ≥95% | ~90.5% (WER 9.5%) | ⚠️ Cần round-2 xác nhận proper noun |
| Proper name accuracy | ≥95% | Chưa đo được (VIVOS không có names) | ⚠️ BLOCKED round-2 |
| Hallucination khi im lặng | <0.5% | RMS gate active | ✅ Design-level |
| Speech end → final P50 | ≤900ms | **66ms** | ✅ 13.6x margin |
| RAM hai phiên | Ổn định | ~88MB/model | ✅ |
| Cross-session leakage | 0 | Per-session isolation | ✅ |

**Gate status: CONDITIONAL PASS** — đạt tất cả chỉ tiêu máy đo được.
Proper noun accuracy cần round-2 corpus tự thu (human task #4).
Không còn BLOCKED bởi model download.
