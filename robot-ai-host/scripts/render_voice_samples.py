"""Render one sample sentence per VieNeu female preset → artifacts/upgrade/voice_samples/.

Run: .venv-hybrid/bin/python scripts/render_voice_samples.py
"""

import time
import wave
from pathlib import Path

import numpy as np

VOICES = ["Trúc Ly", "Ngọc Linh", "Đoan Trang", "Mai Anh", "Thục Đoan", "Thùy Dung", "Ngọc Trân"]
TEXT = "[cười] Chào bạn! Mình là trợ lý AI của trường. Hôm nay mình có thể giúp gì cho bạn nè?"
OUT = Path(__file__).resolve().parent.parent / "artifacts" / "upgrade" / "voice_samples"


def main() -> None:
    from vieneu import Vieneu

    OUT.mkdir(parents=True, exist_ok=True)
    print("loading VieNeu…")
    tts = Vieneu()
    for voice in VOICES:
        t0 = time.monotonic()
        try:
            wav = tts.infer(TEXT, voice=voice, style="doc_truyen")
        except Exception as exc:  # voice missing from presets → skip, keep going
            print(f"SKIP {voice}: {exc}")
            continue
        pcm = (np.clip(np.asarray(wav, dtype=np.float32), -1, 1) * 32767).astype(np.int16)
        path = OUT / f"{voice.replace(' ', '_')}.wav"
        with wave.open(str(path), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(48000)
            f.writeframes(pcm.tobytes())
        print(f"{voice}: {time.monotonic() - t0:.1f}s → {path.name}")


if __name__ == "__main__":
    main()
