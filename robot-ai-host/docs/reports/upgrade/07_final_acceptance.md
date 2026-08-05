# 07 — Acceptance tổng (spec §24, v1.1) — UPDATED 2026-07-27

Date: 2026-07-27
Previous: 2026-07-26
Status: **PARTIAL** → upgraded STT default from CONDITIONAL to LOCKED

## Critical fix this session

**STT mặc định đã chốt**: `stt_streaming_vi` (Sherpa-onnx Zipformer) sau khi:

1. Fix download MLX 8-bit models → root cause: upstream naming mismatch (`model.safetensors` vs `weights.safetensors`). Cả hai model tải được (863MB + 1.64GB) nhưng không decode được.
2. Re-benchmark xác nhận Zipformer: WER 9.51%, P50 0.066s — duy nhất đạt gate ≤900ms.
3. Pipeline integration đã hoàn chỉnh: `SherpaSTTService` + `resolve_stt_candidate()` + `.env` → `STT_CANDIDATE=stt_streaming_vi`.
4. 209 tests pass, 0 regression.

## Per-gate verdict

| # | Tiêu chí §24 | Trạng thái | Căn cứ |
|---|---|---|---|
| 1 | STT mặc định chọn bằng benchmark | **LOCKED** | Zipformer 9.51% WER, 0.066s P50 — duy nhất đạt gate ≤900ms. MLX 8-bit: BROKEN upstream. Round-2 proper noun: human #4 |
| 2 | TTS biểu cảm vượt gate | **BLOCKED (panel)** | Two-tier + VieNeu tích hợp xong, có test; panel ≥8 người (human #5) |
| 3 | Piper fallback hoạt động | PASS | Mặc định + opener tier + per-sentence fallback |
| 4 | Persona tự nhiên, nhất quán | PASS (code) / mic-test pending | Prompt spec 9.4–9.5, PERSONA_NAME config |
| 5 | Read-only tools có nguồn | PASS (code+tests) | 5 tools + metadata nguồn bắt buộc |
| 6 | Action tools có confirmation | PASS (code+tests) | Gateway enforce ngoài LLM |
| 7 | Không false success | PASS (code+tests) | Read-back verify + envelope |
| 8 | Context bounded + summarized | PASS | Cap 8 turns + summary + reset |
| 9 | Tool/memory/session isolation | PASS (code+tests) | Per-session store, per-user memory |
| 10 | Metrics giải thích toàn bộ turn | PASS (server-side) | 16-event timeline |
| 11 | Barge-in đạt target | PENDING (live) | Đường đo có sẵn, cần phiên thật |
| 12 | Repository reproducible | PASS | Lock + inventories + single config source |
| 13 | Limitation ghi trung thực | PASS | Reports + KNOWN_LIMITATIONS |

## Thay đổi từ lần trước

- STT: BLOCKED → **LOCKED**. Zipformer confirmed as default.
- MLX 8-bit: "download fail" → **diagnosed** (upstream naming mismatch). Documented, not a project bug.
- Test suite: 171 → **209 passed** (tăng 38 tests từ Phase-0 refactor + new features).
- Pipeline: SherpaSTTService integration verified end-to-end (smoke test).

**Kết luận**: Máy làm được đã hoàn thành. Các BLOCKED còn lại đều là human tasks
(panel nghe TTS, corpus vòng 2, mic test, soak test, nội dung knowledge thật).
