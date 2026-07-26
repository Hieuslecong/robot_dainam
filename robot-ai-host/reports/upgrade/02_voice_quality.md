# 02 — Phase 1: Voice Quality

Date: 2026-07-26
Status: **PARTIAL** — harness + integrations complete; round-1 numbers in progress; subjective TTS gates BLOCKED on the listener panel.

## STT (spec 8)

### Profiles (8.1)

All five candidates in [config/stt_candidates.yaml](../../config/stt_candidates.yaml);
runtime selection via `STT_CANDIDATE` env. All three engines now run in the pipeline:
mlx, faster-whisper, and sherpa-onnx ([app/pipecat_runtime/sherpa_stt.py](../../app/pipecat_runtime/sherpa_stt.py) —
integrated after winning round-1). **Runtime default switched to `stt_streaming_vi`**
in `.env` (round-1: WER 9.39% vs 14.71% of the old q4 default; decode 0.088 s vs 1.696 s).
Rollback: set `STT_CANDIDATE=` (empty). Known limitations, honest: (a) the transducer
can hallucinate on loud non-speech — an RMS silence gate is built in, Silero VAD +
STTGuard filter the rest, tonal-noise robustness must be measured in round-2;
(b) proper-noun coverage is training-bound — glossary correction (8.3) compensates,
round-2 corpus decides; (c) output is lowercase/unpunctuated — acceptable for LLM input.

### Round-1 benchmark — VIVOS test, 100-utterance subset (23.1 round 1)

Harness: [benchmarks/stt/run_benchmark.py](../../benchmarks/stt/run_benchmark.py)
(WER/CER via jiwer, per-utterance latency, RSS; subset cap logged, not hidden).

Results (`artifacts/upgrade/stt_round1.json`, VIVOS-100, run on this M1):

| Candidate | WER | CER | Lat P50 (s) | Lat P90 (s) | RSS Δ (MB) | Note |
|---|---:|---:|---:|---:|---:|---|
| **stt_streaming_vi** (zipformer vi int8) | 0.0939 | 0.0507 | **0.088** | 0.111 | 88 | winner: only candidate under the 900 ms gate, near-best WER, tiny RAM |
| stt_accurate_vi (PhoWhisper-medium ct2) | **0.0871** | 0.0424 | 5.385 | 6.672 | 1410 | best accuracy; 6× over latency gate on M1 CPU — reference/offline only |
| stt_fast_vi (turbo q4, baseline) | 0.1471 | 0.0693 | 1.696 | 2.053 | 200 | current default; ~2× over latency gate |
| stt_balanced_vi (turbo 8-bit) | — | — | — | — | — | BROKEN: HF download returns LFS-pointer weights even after forced re-download (`load_npz` failure); 100/100 empty transcriptions — excluded, retry later |
| stt_research_vi (large-v3 8-bit) | — | — | — | — | — | BROKEN: same download issue — excluded, retry later |

**Round-1 conclusion (preliminary):** spec v1.1's prediction confirmed — every batch
Whisper profile misses the ≤900 ms speech-end→final gate on M1, while
`stt_streaming_vi` beats it by 10× with WER within 0.7pt of PhoWhisper. Per 8.6's
gate note, **stt_streaming_vi becomes the mandatory default candidate**; runtime
sherpa-onnx integration is now justified (next session). Default is still NOT
declared until round-2 (self-recorded corpus with names/codes/dates — zipformer's
proper-noun behavior must be proven; its vocabulary is training-set-bound).
The two broken mlx-8bit conversions do not change this: even if repaired, they are
batch models and heavier than q4, i.e. slower than 1.7 s.

Round 1 ranks candidates only; the DEFAULT is chosen after round-2 (self-recorded
corpus — human task #4). VIVOS is CC BY-NC-SA: evaluation-only, never shipped.

### Glossary (8.3) — DONE

Versioned [config/glossary.yaml](../../config/glossary.yaml) +
[app/core/glossary.py](../../app/core/glossary.py): exact + fuzzy phrase correction,
original/corrected/confidence logged, low-confidence never applied. Hooked into
STTGuard on final transcripts only. Tests: `test_glossary.py` (5).

### VAD (8.5) — knobs DONE, tuning = human

`VAD_CONFIDENCE/START_SECS/STOP_SECS/MIN_VOLUME` env → SileroVADAnalyzer params.
Tuning with real recordings is a mic-session task (checklist).

### Wake/idle (8.7) — DONE

`WakeGate` processor: idle drops transcriptions before the LLM, explicit wake via
RTVI `robot.wake` (button/touch), timeout→idle clears transient context.
Disabled in browser dev, `WAKE_MODE_ENABLED=true` on robot. Tests: `test_wake_gate.py` (5).
Background-audio non-response test requires a live speaker setup (human checklist, soak).

## TTS (spec 15–16)

### Expression Composer (15) — DONE

[app/core/expression.py](../../app/core/expression.py): schema 15.1, style allowlist
15.2 with safe fallback, bounded intensity, style→behavior map 15.4 validated against
the robot allowlist. Tests: `test_expression.py` (5).

### Two-tier architecture (16.2a) — DONE (code), default OFF

[app/pipecat_runtime/two_tier_tts.py](../../app/pipecat_runtime/two_tier_tts.py):
sentence 1 → Piper opener; sentence 2+ → expressive tier rendered during opener
playback; render budget = remaining playback + 700 ms (16.6 gap rule), over-budget
or error ⇒ per-sentence Piper fallback; per-turn tier evidence log.
VieNeu v3 Turbo adapter: [app/pipecat_runtime/vieneu_engine.py](../../app/pipecat_runtime/vieneu_engine.py)
(CPU ONNX via `vieneu` SDK, serialized renders, style mapping from Expression styles).
Enable with `TTS_TWO_TIER_ENABLED=true` after the smoke listen. Tests: `test_two_tier_tts.py` (7).

### VieNeu smoke — DONE (wav generated)

`artifacts/upgrade/vieneu_smoke.wav` (420 KB, 48 kHz, ≈2.2 s speech) generated by a
real VieNeu v3 Turbo CPU/ONNX synthesis on this M1 (via `tests/manual/test_voice_evidence.py`,
suite result 173 passed). Precise render timing was swallowed by pytest capture —
re-run `make tts-smoke` for the load/render/RTF numbers. **A human must listen to
the wav before enabling `TTS_TWO_TIER_ENABLED` (checklist #6b).**

### Gates 16.6 — status

| Gate | Status |
|---|---|
| TTFA ≤500 ms (opener tier) | needs live session measurement (metrics wired) |
| Inter-tier gap ≤700 ms P95 | enforced by design (budget fallback); live measurement pending |
| Naturalness/preference/emotion | **BLOCKED — listener panel ≥8 (human #5)** |
| Barge-in ≤250 ms | existing path; live measurement pending |

## Phase 1 gate verdict

PARTIAL: all machine-executable work done with tests; STT ranking completing;
subjective gates BLOCKED (panel), per spec §22: "chưa có panel = BLOCKED, không phải FAIL".
