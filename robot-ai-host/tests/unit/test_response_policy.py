"""ResponsePolicyProcessor: cumulative streamed-delta enforcement."""

import asyncio

from pipecat.frames.frames import (
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    TextFrame,
)
from pipecat.processors.frame_processor import FrameDirection

from app.processors.response_policy import ResponsePolicyProcessor


class _Sink:
    """Capture frames the processor pushes downstream."""

    def __init__(self, proc):
        self.frames = []
        proc.push_frame = self._push  # type: ignore[method-assign]

    async def _push(self, frame, direction=FrameDirection.DOWNSTREAM):
        self.frames.append(frame)


async def _run(proc, frames):
    for frame in frames:
        await proc.process_frame(frame, FrameDirection.DOWNSTREAM)


def _texts(sink):
    return [f.text for f in sink.frames if isinstance(f, TextFrame)]


def test_streamed_deltas_over_sentence_cap_are_swallowed():
    proc = ResponsePolicyProcessor(max_sentences=2, max_words=1000)
    sink = _Sink(proc)
    deltas = ["Câu một. ", "Câu hai. ", "Câu ba bị cắt. ", "Câu bốn cũng cắt. "]
    asyncio.run(_run(proc, [LLMFullResponseStartFrame(), *map(TextFrame, deltas),
                            LLMFullResponseEndFrame()]))
    assert _texts(sink) == ["Câu một. ", "Câu hai. "]


def test_word_cap_cumulative_across_small_deltas():
    proc = ResponsePolicyProcessor(max_sentences=100, max_words=6)
    sink = _Sink(proc)
    deltas = ["một hai ba ", "bốn năm sáu ", "bảy tám chín "]
    asyncio.run(_run(proc, [LLMFullResponseStartFrame(), *map(TextFrame, deltas),
                            LLMFullResponseEndFrame()]))
    assert _texts(sink) == ["một hai ba ", "bốn năm sáu "]


def test_under_cap_passes_untouched_and_resets_between_responses():
    proc = ResponsePolicyProcessor(max_sentences=2, max_words=1000)
    sink = _Sink(proc)
    one_response = [LLMFullResponseStartFrame(), TextFrame("Ngắn thôi. "),
                    LLMFullResponseEndFrame()]
    asyncio.run(_run(proc, one_response * 3))  # 3 consecutive responses
    assert _texts(sink) == ["Ngắn thôi. "] * 3
