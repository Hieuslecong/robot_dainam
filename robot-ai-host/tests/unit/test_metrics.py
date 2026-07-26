"""Tests for latency metrics tracker."""

import pytest

from app.pipecat_runtime.metrics import LatencyTracker


@pytest.mark.asyncio
async def test_record_and_summary():
    tracker = LatencyTracker()
    for v in [100, 200, 300, 400, 500]:
        await tracker.record("test_metric", v)
    summary = await tracker.get_summary("test_metric")
    assert summary["count"] == 5
    assert summary["p50"] == 300.0
    assert summary["max"] == 500.0


@pytest.mark.asyncio
async def test_empty_summary():
    tracker = LatencyTracker()
    summary = await tracker.get_summary("nonexistent")
    assert summary == {}


@pytest.mark.asyncio
async def test_single_value():
    tracker = LatencyTracker()
    await tracker.record("single", 42.0)
    summary = await tracker.get_summary("single")
    assert summary["count"] == 1
    assert summary["p50"] == 42.0
    assert summary["max"] == 42.0


@pytest.mark.asyncio
async def test_reset():
    tracker = LatencyTracker()
    await tracker.record("metric", 100)
    await tracker.reset()
    summary = await tracker.get_summary("metric")
    assert summary == {}


@pytest.mark.asyncio
async def test_get_all_summaries():
    tracker = LatencyTracker()
    await tracker.record("a", 10)
    await tracker.record("b", 20)
    summaries = await tracker.get_all_summaries()
    assert "a" in summaries
    assert "b" in summaries
    assert summaries["a"]["count"] == 1
    assert summaries["b"]["count"] == 1


@pytest.mark.asyncio
async def test_percentiles_accuracy():
    tracker = LatencyTracker()
    # 100 values from 1 to 100
    for i in range(1, 101):
        await tracker.record("p_test", float(i))
    summary = await tracker.get_summary("p_test")
    assert summary["count"] == 100
    # P50 should be around 50
    assert 49 <= summary["p50"] <= 51
    # P90 should be around 90
    assert 89 <= summary["p90"] <= 91
    # P95 should be around 95
    assert 94 <= summary["p95"] <= 96
    assert summary["max"] == 100.0


@pytest.mark.asyncio
async def test_jsonl_evidence_and_filters(tmp_path):
    path = tmp_path / "runtime.jsonl"
    tracker = LatencyTracker(path)
    await tracker.record("latency", 100, session_id="s1", profile="mock")
    await tracker.record("latency", 300, session_id="s2", profile="google_vi")

    assert path.is_file()
    assert len(path.read_text(encoding="utf-8").strip().splitlines()) == 2
    s1 = await tracker.get_all_summaries(session_id="s1")
    assert s1["latency"]["count"] == 1
    assert s1["latency"]["p50"] == 100.0
    google = await tracker.get_all_summaries(profile="google_vi")
    assert google["latency"]["p50"] == 300.0
