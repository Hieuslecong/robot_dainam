"""Unified turn-timeline tests — spec 17.1/17.3."""

import pytest

from app.pipecat_runtime.metrics import LatencyTracker
from app.pipecat_runtime.observers import TurnTimeline


def test_timeline_event_names_match_spec():
    assert LatencyTracker.TIMELINE_EVENTS == (
        "physical_speech_start",
        "vad_speech_start",
        "physical_speech_end",
        "vad_speech_end",
        "turn_finalized",
        "stt_final",
        "llm_request_start",
        "llm_first_token",
        "first_speakable_chunk",
        "tts_request_start",
        "tts_first_audio",
        "server_audio_sent",
        "client_audio_received",
        "client_audible_start",
        "interruption_detected",
        "client_audio_stopped",
    )


def test_first_occurrence_wins():
    turn = TurnTimeline()
    turn.mark("tts_first_audio", 10.0)
    turn.mark("tts_first_audio", 20.0)
    assert turn.events["tts_first_audio"] == 10.0


def test_segments_and_offsets():
    turn = TurnTimeline()
    turn.mark("vad_speech_start", 100.0)
    turn.mark("vad_speech_end", 101.0)
    turn.mark("stt_final", 101.9)
    turn.mark("llm_first_token", 102.5)
    assert turn.offset_ms("stt_final") == pytest.approx(1900.0)
    assert turn.segment_ms("stt_final", "llm_first_token") == pytest.approx(600.0)
    assert turn.segment_ms("stt_final", "missing") is None


async def test_summary_shape_has_required_percentiles(tmp_path):
    tracker = LatencyTracker(jsonl_path=tmp_path / "m.jsonl")
    for v in (100, 200, 300, 400, 500):
        await tracker.record(LatencyTracker.METRIC_SEG_STT_TO_FIRST_TOKEN, v)
    summary = await tracker.get_summary(LatencyTracker.METRIC_SEG_STT_TO_FIRST_TOKEN)
    assert set(summary) == {"count", "p50", "p90", "p95", "max"}
    assert summary["count"] == 5
    assert summary["p50"] == 300
