"""Manual evidence runs (long): VieNeu smoke + STT round-1 benchmark.

Gated by a flag file so the normal test suite never triggers model downloads
or long benchmarks. Create ``artifacts/upgrade/RUN_EVIDENCE`` to enable, run

    .venv-hybrid/bin/python -m pytest tests/manual -q -s

then delete the flag. These are evidence generators, not assertions of quality.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FLAG = ROOT / "artifacts" / "upgrade" / "RUN_EVIDENCE"

pytestmark = pytest.mark.skipif(not FLAG.exists(), reason="evidence flag file absent")


def test_vieneu_smoke_generates_wav():
    import runpy
    import sys

    sys.argv = ["vieneu_smoke.py"]
    cwd = Path.cwd()
    assert (ROOT / "benchmarks/tts/vieneu_smoke.py").exists()
    import os

    os.chdir(ROOT)
    try:
        runpy.run_path(str(ROOT / "benchmarks/tts/vieneu_smoke.py"), run_name="__main__")
    finally:
        os.chdir(cwd)
    wav = ROOT / "artifacts/upgrade/vieneu_smoke.wav"
    assert wav.exists() and wav.stat().st_size > 100_000


def test_stt_round1_benchmark_completes():
    import os
    import sys

    sys.argv = [
        "run_benchmark.py", "--limit", "100",
        "--candidates", "stt_balanced_vi", "stt_accurate_vi",
        "stt_research_vi", "stt_streaming_vi",
    ]
    import runpy

    cwd = Path.cwd()
    os.chdir(ROOT)
    try:
        runpy.run_path(str(ROOT / "benchmarks/stt/run_benchmark.py"), run_name="__main__")
    finally:
        os.chdir(cwd)
    assert (ROOT / "artifacts/upgrade/stt_round1.json").exists()
