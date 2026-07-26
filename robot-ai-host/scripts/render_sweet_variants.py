"""Render "ngọt ngào truyền cảm" variants → artifacts/upgrade/voice_samples/sweet/.

Sweet = doc_truyen style, near-original pitch, gentle pacing. Compares
Đoan Trang against the other soft female presets, plus mild speed variants.
Pick by ear, then set VIENEU_VOICE / VIENEU_SPEED / VIENEU_TEMPERATURE in .env.

Run: .venv-hybrid/bin/python scripts/render_sweet_variants.py
"""

import time
import wave
from pathlib import Path

import numpy as np

from app.pipecat_runtime.vieneu_engine import speed_shift

TEXT = (
    "Chào bạn nè. Mình là trợ lý AI của trường đây. "
    "Hôm nay bạn thấy trong người thế nào? Có gì để mình giúp bạn không nè?"
)
# (label, voice, speed, temperature) — sweet zone: speed ≤1.03, temp ~0.85
VARIANTS = [
    ("DoanTrang_1.00x_t0.85", "Đoan Trang", 1.00, 0.85),
    ("DoanTrang_1.03x_t0.85", "Đoan Trang", 1.03, 0.85),
    ("DoanTrang_0.97x_t0.85", "Đoan Trang", 0.97, 0.85),
    ("ThucDoan_1.00x_t0.85", "Thục Đoan", 1.00, 0.85),
    ("ThuyDung_1.00x_t0.85", "Thùy Dung", 1.00, 0.85),
    ("NgocTran_1.00x_t0.85", "Ngọc Trân", 1.00, 0.85),
    ("TrucLy_1.00x_t0.85", "Trúc Ly", 1.00, 0.85),
]
OUT = Path(__file__).resolve().parent.parent / "artifacts" / "upgrade" / "voice_samples" / "sweet"


def main() -> None:
    from vieneu import Vieneu

    OUT.mkdir(parents=True, exist_ok=True)
    print("loading VieNeu…")
    tts = Vieneu()
    for label, voice, speed, temp in VARIANTS:
        t0 = time.monotonic()
        try:
            raw = tts.infer(TEXT, voice=voice, style="doc_truyen", temperature=temp)
        except Exception as exc:
            print(f"SKIP {label}: {exc}")
            continue
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
