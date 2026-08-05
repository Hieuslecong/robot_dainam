# Code Review — uvloop + intro fix session

## Summary

| Category | Count |
|---|---|
| Critical bugs | 0 |
| Medium bugs | 1 (immediately fixed) |
| Low issues | 2 |
| Regressions | 0 |
| Missing tests | 1 new module |

---

## Bugs Found

### 🐛 Bug 1 [MEDIUM — FIXED]: Piper profile 8s delay before intro

**File:** `worker_factory.py:164-168`

**Vấn đề:** Poll `engine.ready` loop chạy 16×0.5s = 8s kể cả khi `engine is None` (Piper TTS). Piper không có warm-up nên delay này vô nghĩa.

```python
# ❌ Before fix
engine = getattr(bundle, "vieneu_engine", None)  # None for Piper
for _ in range(16):
    if engine is not None and engine.ready:       # never True → 8s wasted
        break
    await _asyncio.sleep(0.5)
```

**Fix:** Bọc loop trong `if engine is not None:` → Piper instant, VieNeu đợi max 8s.

---

## Low Issues

### ⚠️ Issue 1: `uvloop` import order
main.py imports `asyncio` at line 6, THEN sets uvloop policy at line 10. Đúng thứ tự, nhưng nếu ai đó import asyncio trước khi main.py được import, policy sẽ không được set. Đây là behavior mong muốn (graceful fallback).

### ⚠️ Issue 2: `pipeline_factory.py` — Piper path không pass `vieneu_engine`
Line 420-422 gọi `_assemble_hybrid_bundle(..., vieneu_engine=None)` — thiếu explicit `=None`. Python tự default về `None` từ function signature nên OK, nhưng code hơi ambiguous. Non-blocking.

---

## Regressions — None ✅

| Check | Result |
|---|---|
| All 193 tests | ✅ Pass |
| /health | ✅ |
| /client dashboard | ✅ |
| /client/chat voice | ✅ |
| /robot | ✅ |
| ICE negotiation | ✅ |
| TURN credential generation | ✅ |
| Session creation | ✅ |
| Admin API | ✅ |

---

## Missing Tests

| Module | Priority |
|---|---|
| `app/pipecat_runtime/ice_utils.py` | Low (đã tested indirectly) |
| `app/pipecat_runtime/worker_factory.py:on_client_connected` (intro poll) | Medium |

### Đề xuất test cho worker_factory intro:

```python
async def test_intro_skips_wait_when_no_engine():
    """Piper/mock profiles should not wait for non-existent VieNeu."""
    # bundle.vieneu_engine = None → intro fires immediately
    ...

async def test_intro_waits_for_vieneu_ready():
    """VieNeu profile waits max 8s for engine.ready."""
    ...
```

---

## Code Quality

| File | Status |
|---|---|
| `main.py` uvloop | ✅ Clean, graceful fallback |
| `pipeline_factory.py` | ✅ Clean |
| `worker_factory.py` | ✅ Bug fixed, clean |
| `ice_utils.py` | ✅ No issues |
| `admin.py` | ✅ Upload limits added |
| `pyproject.toml` | ✅ uvloop>=0.19 added |

---

## Edge Cases Checked

| Scenario | Behavior |
|---|---|
| uvloop not installed | Graceful fallback, asyncio default |
| VieNeu warm-up >8s | Falls through, queue `TTSSpeakFrame` (may fail silently) |
| Piper profile (no VieNeu) | Skip wait, queue immediately |
| Mock profile | Skip wait, queue immediately |
| Multi-client concurrent | Each gets own pipeline + bundle, no shared state |
| TURN API unreachable | Falls back to static ICE servers |
| Admin upload >10MB | HTTP 413 |
| Admin upload wrong type | HTTP 400 |
