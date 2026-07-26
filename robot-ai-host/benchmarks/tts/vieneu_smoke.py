"""VieNeu v3 Turbo real-synthesis smoke test — writes wav + timing evidence."""

import time

import numpy as np
import soundfile as sf
from vieneu import Vieneu

t0 = time.monotonic()
tts = Vieneu()  # v3turbo default; CPU -> ONNX int8
load_s = time.monotonic() - t0

TEXT = "Chào bạn, mình là trợ lý AI của trường. Mình có thể giúp gì cho bạn hôm nay?"
t1 = time.monotonic()
audio = tts.infer(TEXT)
render_s = time.monotonic() - t1

SR = 48000
sf.write("artifacts/upgrade/vieneu_smoke.wav", np.asarray(audio, dtype="float32"), SR)
dur = len(audio) / SR
print(f"load_s={load_s:.1f} render_s={render_s:.2f} audio_s={dur:.2f} rtf={render_s / dur:.2f}")
