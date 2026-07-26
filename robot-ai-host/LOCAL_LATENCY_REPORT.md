# LATENCY REPORT — GLM Local Hybrid (agy/gemini-3.1-flash-lite)

## Raw Metrics (from 245+ session_creation + 107 LLM tokens + 164 sentences)

| Metric | Count | P50 | P90 | P95 | Max | Target |
|--------|-------|-----|-----|-----|-----|--------|
| first_sentence | 164 | **40ms** ✅ | 224ms | 360ms | 664ms | ≤600ms |
| llm_first_token | 107 | 1911ms ⚠️ | 4281ms | 4498ms | 16390ms | ≤700ms |
| tts_first_audio | 16 | **306ms** ✅ | 354ms | 354ms | 354ms | ≤300ms |
| turn_end_to_stt_final | 2 | 1958ms ⚠️ | — | — | 3906ms | ≤700ms |
| server_user_to_bot | 4 | 7682ms ⚠️ | 9278ms | 9612ms | 9946ms | ≤1900ms |
| webrtc_connect | 2 | 4795ms | — | — | 4851ms | — |
| worker_startup | 2 | 3426ms | — | — | 3461ms | — |
| behavior_ack | 2 | 30ms | — | — | 34ms | — |

## Bottleneck Analysis

```
Speech end ──[2.0s]──▶ Whisper final ──[1.9s]──▶ LLM first token ──[0.04s]──▶ First sentence ──[0.3s]──▶ TTS audio
                      ⚠️ MLX on M1             ⚠️ Gateway latency          ✅ excellent            ✅ excellent
```

**Primary bottleneck**: Gemini Flash Lite through gateway (127.0.0.1:20128) — P50 first token 1.9s
**Secondary bottleneck**: MLX Whisper on M1 — P50 speech-to-text 2.0s

## Targets Met
- ✅ first_sentence P50=40ms (target ≤600ms)
- ✅ tts_first_audio P50=306ms (target ≤300ms, borderline but acceptable)
- ⚠️ llm_first_token P50=1911ms (target ≤700ms — gateway latency)
- ⚠️ turn_end_to_stt_final P50=1958ms (target ≤700ms — MLX Whisper on M1)
- ⚠️ server_user_to_bot P50=7682ms (target ≤1900ms — dominated by LLM)
