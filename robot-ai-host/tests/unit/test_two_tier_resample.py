"""Resample + no-sentence-dropped guarantees for the two-tier TTS."""

import asyncio

from app.pipecat_runtime.two_tier_tts import TwoTierTTSService, resample_s16

RATE = 24000


def test_resample_identity():
    audio = b"\x01\x00" * 1000
    assert resample_s16(audio, RATE, RATE) == audio


def test_resample_48k_halves_length():
    audio = b"\x01\x00" * 4800  # 100 ms at 48 kHz
    out = resample_s16(audio, 48000, 24000)
    assert abs(len(out) - len(audio) // 2) <= 2


def test_resample_22050_to_24000_grows():
    audio = b"\x01\x00" * 2205
    out = resample_s16(audio, 22050, 24000)
    assert len(out) // 2 in range(2380, 2420)


def test_mixed_rate_engines_normalized_and_both_sentences_spoken():
    async def opener(text):
        return b"\x01\x00" * 2205, 22050  # piper-like

    async def expressive(text):
        return b"\x01\x00" * 4800, 48000  # vieneu-like

    service = TwoTierTTSService(opener=opener, expressive=expressive, name="TT")

    async def run():
        frames = []
        for sentence in ["Câu một.", "Câu hai."]:
            async for frame in service.run_tts(sentence, "ctx"):
                frames.append(frame)
        return frames

    frames = asyncio.run(run())
    assert len(frames) >= 2
    assert {f.sample_rate for f in frames} == {service._configured_rate}
    assert [t for t, _ in service.tier_log] == ["opener", "expressive"]


def test_opener_failure_drops_sentence_loudly_but_not_turn():
    calls = []

    async def opener(text):
        if text == "Hỏng.":
            raise RuntimeError("piper down")
        calls.append(text)
        return b"\x01\x00" * 240, 24000

    service = TwoTierTTSService(opener=opener, expressive=None, name="TT")

    async def run():
        frames = []
        for sentence in ["Hỏng.", "Còn nói được."]:
            async for frame in service.run_tts(sentence, "ctx"):
                frames.append(frame)
        return frames

    frames = asyncio.run(run())
    assert calls == ["Còn nói được."]
    assert len(frames) >= 1
