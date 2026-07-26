"""Render Đoan Trang teen-ification variants → artifacts/upgrade/voice_samples/teen/.

Variants: speed (pitch+tempo) x temperature. Pick by ear, then set
VIENEU_SPEED / VIENEU_TEMPERATURE in .env.

Run: .venv-hybrid/bin/python scripts/render_teen_variants.py
"""

import time
import wave
from pathlib import Path

import numpy as np

from app.pipecat_runtime.vieneu_engine import speed_shift

VOICE = "Đoan Trang"
TEXT = (
    "[cười] Chào bạn! Mình là trợ lý AI của trường nè. "
    "Hôm nay có gì hay ho để mình giúp bạn không nè?"
)
# (label, speed, temperature)
VARIANTS = [
    ("goc_1.00x_t0.8", 1.00, 0.8),
    ("teen_1.05x_t0.8", 1.05, 0.8),
    ("teen_1.08x_t0.8", 1.08, 0.8),
    ("teen_1.05x_t1.0", 1.05, 1.0),
    ("teen_1.08x_t1.0", 1.08, 1.0),
    ("teen_1.12x_t1.0", 1.12, 1.0),
]
OUT = Path(__file__).resolve().parent.parent / "artifacts" / "upgrade" / "voice_samples" / "teen"


def main() -> None:
    from vieneu import Vieneu

    OUT.mkdir(parents=True, exist_ok=True)
    print("loading VieNeu…")
    tts = Vieneu()
    for label, speed, temp in VARIANTS:
        t0 = time.monotonic()
        raw = tts.infer(TEXT, voice=VOICE, style="doc_truyen", temperature=temp)
        shifted = speed_shift(np.asarray(raw, dtype=np.float32), speed)
        pcm = (np.clip(shifted, -1, 1) * 32767).astype(np.int16)
        path = OUT / f"{label}.wav"
        with wave.open(str(path), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(48000)
            f.writeframes(pcm.tobytes())
        print(f"{label}: {time.monotonic() - t0:.1f}s → {path.name}")


if __name__ == "__main__":
    main()
