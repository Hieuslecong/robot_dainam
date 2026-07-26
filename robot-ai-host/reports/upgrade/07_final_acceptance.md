# 07 — Acceptance tổng (spec §24, v1.1)

Date: 2026-07-26
Per-phase evidence: reports 01–06. Test suite: **171 passed** (Python) + **5 passed** (frontend) + build OK.

| # | Tiêu chí §24 | Trạng thái | Căn cứ |
|---|---|---|---|
| 1 | STT mặc định chọn bằng benchmark | **ROUND-1 DONE** | Zipformer streaming thắng round-1 (WER 9.39%, P50 0.088s — duy nhất đạt gate ≤900ms); PhoWhisper WER tốt nhất (8.71%) nhưng 5.4s; 2 bản mlx-8bit hỏng download (ghi nhận). Chốt mặc định cần round-2 corpus tự thu (human #4) + tích hợp runtime sherpa |
| 2 | TTS biểu cảm vượt gate | **BLOCKED (panel)** | Two-tier + VieNeu tích hợp xong, có test; gate chủ quan cần panel ≥8 người (human #5) — spec: BLOCKED ≠ FAIL |
| 3 | Piper fallback hoạt động | PASS | Mặc định hiện hành + opener tier + per-sentence fallback (tested) |
| 4 | Persona tự nhiên, nhất quán | PASS (code) / mic-test pending | Spec 9.4–9.5 prompt, PERSONA_NAME config; nghe thật = human #3 |
| 5 | Read-only tools có nguồn | PASS (code+tests) | 5 tools + metadata nguồn bắt buộc; không bịa nguồn (tested); nội dung thật = human #7 |
| 6 | Action tools có confirmation | PASS (code+tests) | Gateway enforce ngoài LLM; zero unauthorized (tested) |
| 7 | Không false success | PASS (code+tests) | Read-back verify + envelope; interface-only tools không tính |
| 8 | Context bounded + summarized | PASS | Phase 0 (cap 8 turns + summary + reset), tests |
| 9 | Tool/memory/session isolation | PASS (code+tests) | Per-session store, per-user memory file, audit; runtime soak = human #1 |
| 10 | Metrics giải thích toàn bộ turn | PASS (server-side) | 16-event timeline + segments + router metrics; physical_* cần mic tham chiếu |
| 11 | Barge-in đạt target | PENDING (live) | Đường đo có sẵn (client barge_in.stopped); cần phiên thật |
| 12 | Repository reproducible | PASS | Lock + inventories + candidates/config đơn nguồn |
| 13 | Limitation ghi trung thực | PASS | Reports 01–06 + HUMAN_TASK_CHECKLIST + KNOWN_LIMITATIONS |

**Kết luận trung thực: PARTIAL** — đúng kỳ vọng prompt v1.1. Mọi mục máy làm được đã xong kèm test;
các mục còn lại chờ: benchmark re-run (đang queue), panel nghe, mic test, soak, corpus vòng 2, nội dung knowledge thật, live agent eval.
