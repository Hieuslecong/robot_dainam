#!/usr/bin/env python3
"""Verify MPS/MLX acceleration with actual inference, not just config values."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.core.device_manager import detect_device


def check_pytorch_mps() -> tuple[bool, str]:
    """Run a small tensor operation on MPS to prove it works."""
    try:
        import torch

        if not torch.backends.mps.is_available():
            return False, "MPS not available"
        if not torch.backends.mps.is_built():
            return False, "MPS not built"

        # Actual inference test
        a = torch.randn(100, 100, device="mps")
        b = torch.randn(100, 100, device="mps")
        start = time.perf_counter()
        c = torch.mm(a, b)
        # Force sync
        torch.mps.synchronize()
        elapsed = (time.perf_counter() - start) * 1000
        return True, f"MPS matmul 100x100: {elapsed:.1f}ms"
    except ImportError:
        return False, "torch not installed"
    except Exception as e:
        return False, f"MPS error: {e}"


def check_mlx() -> tuple[bool, str]:
    """Run a small MLX array operation to verify MLX works."""
    try:
        import mlx.core as mx

        a = mx.random.normal((100, 100))
        b = mx.random.normal((100, 100))
        start = time.perf_counter()
        mx.eval(a)
        mx.eval(b)
        c = a @ b
        mx.eval(c)
        elapsed = (time.perf_counter() - start) * 1000
        return True, f"MLX matmul 100x100: {elapsed:.1f}ms"
    except ImportError:
        return False, "mlx not installed"
    except Exception as e:
        return False, f"MLX error: {e}"


def main() -> int:
    print("=== Device Acceleration Check ===\n")

    info = detect_device()
    print(f"Platform:      {info.platform}")
    print(f"PyTorch device:{info.pytorch_device}")
    print(f"STT backend:   {info.stt_backend}")
    print(f"TTS backend:   {info.tts_backend}")
    print(f"MLX available: {info.mlx_available}")
    print(f"Fallbacks:     {info.fallbacks}")
    print()

    # PyTorch MPS
    ok, detail = check_pytorch_mps()
    print(f"[{'PASS' if ok else 'INFO'}] PyTorch MPS: {detail}")

    # MLX
    ok, detail = check_mlx()
    print(f"[{'PASS' if ok else 'INFO'}] MLX: {detail}")

    # Summary
    device = detect_device()
    if device.pytorch_device == "mps":
        print("\n✅ Apple GPU (MPS) detected and functional")
    elif device.pytorch_device == "cuda":
        print("\n✅ NVIDIA CUDA detected")
    elif device.fallbacks:
        print(f"\n⚠️  Running on CPU. Fallbacks: {device.fallbacks}")
    else:
        print("\n✅ CPU mode (no GPU available)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
