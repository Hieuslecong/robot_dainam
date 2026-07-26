"""TTS streaming soak: render sentences continuously, watch RTF/memory/locks.

Run (default 30 min):  .venv-hybrid/bin/python scripts/soak_stream_tts.py
Short check (2 min):   .venv-hybrid/bin/python scripts/soak_stream_tts.py 2
"""

import asyncio
import resource
import sys
import time

SENTENCES = [
    "Chào bạn, mình là trợ lý AI của trường nè!",
    "Thư viện nằm ở tầng ba tòa nhà A, mở cửa từ tám giờ đến hai mươi giờ.",
    "[cười] Câu này vui ghê, mình thích lắm luôn đó.",
    "Hạn đăng ký học phần học kỳ một là ngày hai mươi lăm tháng tám.",
    "Bạn nhớ nghỉ ngơi đầy đủ, uống đủ nước và ngủ sớm nha.",
]


async def main(minutes: float) -> None:
    from app.pipecat_runtime.vieneu_engine import VIENEU_SAMPLE_RATE, VieNeuEngine

    engine = VieNeuEngine(voice="Đoan Trang", speed=1.08)
    engine.start_warm_up()
    while not engine.ready:
        await asyncio.sleep(1)
    print("vieneu loaded — soaking…")

    deadline = time.monotonic() + minutes * 60
    n = 0
    worst_rtf = 0.0
    while time.monotonic() < deadline:
        sentence = SENTENCES[n % len(SENTENCES)]
        t0 = time.monotonic()
        total = 0
        first_chunk_s = None
        async for pcm, _rate in engine.synthesize_stream(sentence, style="cheerful"):
            if first_chunk_s is None:
                first_chunk_s = time.monotonic() - t0
            total += len(pcm)
        wall = time.monotonic() - t0
        audio_s = total / 2 / VIENEU_SAMPLE_RATE
        rtf = wall / audio_s if audio_s else 0.0
        worst_rtf = max(worst_rtf, rtf)
        rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)
        n += 1
        print(
            f"#{n} ttfa={first_chunk_s:.2f}s wall={wall:.2f}s audio={audio_s:.2f}s "
            f"rtf={rtf:.2f} rss={rss_mb:.0f}MB"
        )
    print(f"DONE: {n} sentences, worst RTF {worst_rtf:.2f} "
          f"({'OK' if worst_rtf < 1.0 else 'SLOWER THAN REALTIME'})")


if __name__ == "__main__":
    asyncio.run(main(float(sys.argv[1]) if len(sys.argv) > 1 else 30.0))
