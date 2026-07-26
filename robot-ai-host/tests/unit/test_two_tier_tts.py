"""Two-tier TTS routing tests (spec 16.2a) with deterministic fake engines."""

import asyncio
import time

import pytest

from app.pipecat_runtime.two_tier_tts import (
    MAX_INTER_TIER_GAP_S,
    TwoTierTTSService,
    _TurnState,
)

RATE = 24000
PCM_HALF_SECOND = b"\x00\x00" * (RATE // 2)


def _opener_fn(calls):
    async def opener(text):
        calls.append(text)
        return PCM_HALF_SECOND, RATE

    return opener


def _expressive_fn(calls, delay_s=0.0):
    async def expressive(text):
        if delay_s:
            await asyncio.sleep(delay_s)
        calls.append(text)
        return PCM_HALF_SECOND, RATE

    return expressive


def _service(opener, expressive):
    return TwoTierTTSService(
        opener=opener, expressive=expressive, name="TwoTierTTS"
    )


async def _collect(service, sentences, context_id="ctx-1"):
    frames = []
    for sentence in sentences:
        async for frame in service.run_tts(sentence, context_id):
            frames.append(frame)
    return frames


def test_first_sentence_uses_opener_later_use_expressive():
    opener_calls, expressive_calls = [], []
    service = _service(_opener_fn(opener_calls), _expressive_fn(expressive_calls))
    frames = asyncio.run(_collect(service, ["Câu một.", "Câu hai.", "Câu ba."]))
    assert opener_calls == ["Câu một."]
    assert expressive_calls == ["Câu hai.", "Câu ba."]
    assert [t for t, _ in service.tier_log] == ["opener", "expressive", "expressive"]
    assert len(frames) >= 3  # each sentence streams as one or more chunks
    assert all(f.sample_rate == service._configured_rate for f in frames)


def test_expressive_timeout_falls_back_to_opener():
    opener_calls, expressive_calls = [], []
    service = TwoTierTTSService(
        opener=_opener_fn(opener_calls),
        expressive=_expressive_fn(expressive_calls, delay_s=5.0),
        expressive_min_render_estimate_s=0.05,
        name="TwoTierTTS",
    )
    # Force a near-zero mask window so the slow expressive render times out.
    asyncio.run(_collect(service, ["Một.", "Hai."]))
    assert opener_calls == ["Một.", "Hai."]
    assert expressive_calls == []
    assert [t for t, _ in service.tier_log] == ["opener", "opener"]


def test_expressive_error_falls_back_to_opener():
    opener_calls = []

    async def broken(text):
        raise RuntimeError("engine down")

    service = _service(_opener_fn(opener_calls), broken)
    asyncio.run(_collect(service, ["Một.", "Hai."]))
    assert opener_calls == ["Một.", "Hai."]


def test_no_expressive_engine_all_opener():
    opener_calls = []
    service = _service(_opener_fn(opener_calls), None)
    asyncio.run(_collect(service, ["Một.", "Hai."]))
    assert opener_calls == ["Một.", "Hai."]


def test_new_context_resets_to_opener_tier():
    opener_calls, expressive_calls = [], []
    service = _service(_opener_fn(opener_calls), _expressive_fn(expressive_calls))
    asyncio.run(_collect(service, ["A.", "B."], context_id="ctx-1"))
    asyncio.run(_collect(service, ["C."], context_id="ctx-2"))
    assert opener_calls == ["A.", "C."]
    assert expressive_calls == ["B."]


def test_budget_is_playback_remaining_plus_gap():
    turn = _TurnState(context_id="c", started_at=time.monotonic(), queued_audio_s=2.0)
    service = _service(_opener_fn([]), None)
    budget = service._budget_for_expressive(turn)
    assert 1.9 + MAX_INTER_TIER_GAP_S < budget <= 2.0 + MAX_INTER_TIER_GAP_S


def test_single_voice_mode_uses_expressive_for_all_sentences():
    opener_calls, expressive_calls = [], []
    service = TwoTierTTSService(
        opener=_opener_fn(opener_calls),
        expressive=_expressive_fn(expressive_calls),
        opener_first=False,
        name="TwoTierTTS",
    )
    asyncio.run(_collect(service, ["Câu một.", "Câu hai."]))
    assert opener_calls == []
    assert expressive_calls == ["Câu một.", "Câu hai."]
    assert [t for t, _ in service.tier_log] == ["expressive", "expressive"]


def test_single_voice_mode_first_sentence_falls_back_on_error():
    opener_calls = []

    async def broken(text):
        raise RuntimeError("engine down")

    service = TwoTierTTSService(
        opener=_opener_fn(opener_calls),
        expressive=broken,
        opener_first=False,
        name="TwoTierTTS",
    )
    asyncio.run(_collect(service, ["Một."]))
    assert opener_calls == ["Một."]


def _stream_fn(calls, chunks=3, delay_s=0.0, fail_after=None):
    async def stream(text):
        calls.append(text)
        for i in range(chunks):
            if fail_after is not None and i >= fail_after:
                raise RuntimeError("stream died")
            if delay_s:
                await asyncio.sleep(delay_s)
            yield PCM_HALF_SECOND, RATE

    return stream


def test_streaming_expressive_yields_chunks_as_frames():
    stream_calls, opener_calls = [], []
    service = TwoTierTTSService(
        opener=_opener_fn(opener_calls),
        expressive=None,
        expressive_stream=_stream_fn(stream_calls, chunks=3),
        opener_first=False,
        name="TwoTierTTS",
    )
    frames = asyncio.run(_collect(service, ["Câu một.", "Câu hai."]))
    assert stream_calls == ["Câu một.", "Câu hai."]
    assert opener_calls == []
    assert [t for t, _ in service.tier_log] == ["expressive", "expressive"]
    assert len(frames) == 6  # 3 chunks per sentence, streamed straight through
    assert all(f.sample_rate == service._configured_rate for f in frames)


def test_streaming_first_chunk_error_falls_back_to_opener():
    opener_calls = []

    async def broken_stream(text):
        raise RuntimeError("engine down")
        yield  # pragma: no cover — makes this an async generator

    service = TwoTierTTSService(
        opener=_opener_fn(opener_calls),
        expressive=None,
        expressive_stream=broken_stream,
        opener_first=False,
        name="TwoTierTTS",
    )
    asyncio.run(_collect(service, ["Một."]))
    assert opener_calls == ["Một."]
    assert [t for t, _ in service.tier_log] == ["opener"]


def test_streaming_midstream_error_keeps_partial_audio_no_opener():
    stream_calls, opener_calls = [], []
    service = TwoTierTTSService(
        opener=_opener_fn(opener_calls),
        expressive=None,
        expressive_stream=_stream_fn(stream_calls, chunks=3, fail_after=2),
        opener_first=False,
        name="TwoTierTTS",
    )
    frames = asyncio.run(_collect(service, ["Một."]))
    # 2 chunks played, then abort — never re-spoken by the opener voice.
    assert len(frames) == 2
    assert opener_calls == []
    assert [t for t, _ in service.tier_log] == ["expressive"]


def test_barge_in_cancel_closes_engine_stream():
    # Cancelling run_tts mid-stream (pipecat interruption) must aclose the
    # engine generator so its finally runs and the render lock is freed.
    closed = {"flag": False}

    async def slow_stream(text):
        try:
            yield PCM_HALF_SECOND, RATE
            await asyncio.sleep(60)  # consumer gets cancelled while waiting here
            yield PCM_HALF_SECOND, RATE
        finally:
            closed["flag"] = True

    service = TwoTierTTSService(
        opener=_opener_fn([]),
        expressive=None,
        expressive_stream=slow_stream,
        opener_first=False,
        name="TwoTierTTS",
    )

    async def scenario():
        async def consume():
            async for _ in service.run_tts("Một câu dài.", "ctx-1"):
                pass

        task = asyncio.create_task(consume())
        await asyncio.sleep(0.1)  # first chunk consumed, stream now sleeping
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(scenario())
    assert closed["flag"] is True


def test_engine_stream_cancel_releases_lock():
    # Barge-in: consumer closes the stream mid-render → producer thread must
    # exit and the engine lock must be free for the next sentence.
    import numpy as np

    from app.pipecat_runtime.vieneu_engine import VieNeuEngine

    class FakeTTS:
        def infer_stream(self, text, **kwargs):
            for _ in range(50):
                yield np.zeros(4800, dtype=np.float32)

    async def scenario():
        engine = VieNeuEngine()
        engine._tts = FakeTTS()
        gen = engine.synthesize_stream("Xin chào.")
        await gen.__anext__()  # consume one chunk
        await gen.aclose()  # barge-in
        # Lock must be re-acquirable promptly.
        await asyncio.wait_for(engine._lock.acquire(), timeout=5.0)
        engine._lock.release()

    asyncio.run(scenario())


def test_empty_sentence_skipped():
    service = _service(_opener_fn([]), None)
    frames = asyncio.run(_collect(service, ["   "]))
    assert frames == []


def test_wordless_sentences_skipped():
    opener_calls = []
    service = _service(_opener_fn(opener_calls), None)
    frames = asyncio.run(
        _collect(service, [".", "…", "!?", "3.", "[cười]", "[cười] Hay quá!"])
    )
    # No letters outside emotion tags → never sent to TTS; real speech passes.
    assert opener_calls == ["[cười] Hay quá!"]
    assert len(frames) >= 1
