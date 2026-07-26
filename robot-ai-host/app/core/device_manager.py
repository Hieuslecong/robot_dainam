"""Unified device detection for Apple Silicon MPS, MLX, CUDA, and CPU fallback."""

from __future__ import annotations

import platform
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class DeviceInfo:
    platform: str
    architecture: str
    pytorch_device: Literal["mps", "cuda", "cpu"]
    pytorch_available: bool
    stt_backend: Literal["mlx", "faster-whisper", "cpu"]
    mlx_available: bool
    tts_backend: str
    llm_endpoint: str = ""
    llm_model: str = ""
    llm_runtime: Literal["metal", "mlx", "cuda", "cpu", "remote", "unknown"] = "unknown"
    fallbacks: list[str] = field(default_factory=list)
    diagnostics: dict[str, str] = field(default_factory=dict)


def detect_device(
    *,
    allow_cpu_fallback: bool = True,
    log_diagnostics: bool = True,
) -> DeviceInfo:
    """Detect optimal compute device with honest fallback reporting."""

    system = platform.system()
    machine = platform.machine()
    is_apple_silicon = system == "Darwin" and machine == "arm64"

    # --- PyTorch MPS ---
    pytorch_device: Literal["mps", "cuda", "cpu"] = "cpu"
    pytorch_available = False
    try:
        import torch  # noqa: F401

        if torch.cuda.is_available():
            pytorch_device = "cuda"
            pytorch_available = True
        elif torch.backends.mps.is_built() and torch.backends.mps.is_available():
            pytorch_device = "mps"
            pytorch_available = True
    except ImportError:
        pass

    # --- MLX ---
    mlx_available = False
    try:
        import mlx.core  # noqa: F401

        mlx_available = True
    except ImportError:
        pass

    # --- STT backend ---
    if mlx_available and is_apple_silicon:
        stt_backend: Literal["mlx", "faster-whisper", "cpu"] = "mlx"
    elif pytorch_device == "cuda":
        stt_backend = "faster-whisper"
    else:
        stt_backend = "cpu"

    # --- TTS backend ---
    tts_backend = _detect_tts_backend(pytorch_device, is_apple_silicon)

    # --- Fallbacks ---
    fallbacks: list[str] = []
    if not pytorch_available and is_apple_silicon:
        fallbacks.append("mps-not-available")
    if not mlx_available and is_apple_silicon:
        fallbacks.append("mlx-not-available")
    if pytorch_device == "cpu" and is_apple_silicon:
        fallbacks.append("mps-fallback-cpu")
    if allow_cpu_fallback and pytorch_device == "cpu":
        fallbacks.append("cpu-fallback-active")

    # --- Diagnostics ---
    diagnostics: dict[str, str] = {}
    if log_diagnostics:
        diagnostics["platform"] = f"{system} {machine}"
        diagnostics["pytorch_device"] = pytorch_device
        diagnostics["mlx_available"] = str(mlx_available)
        if is_apple_silicon and pytorch_device == "cpu":
            diagnostics["warning"] = (
                "Apple Silicon detected but PyTorch MPS not available. "
                "Install PyTorch with MPS support for GPU acceleration."
            )

    return DeviceInfo(
        platform=f"{system} {machine}",
        architecture=machine,
        pytorch_device=pytorch_device,
        pytorch_available=pytorch_available,
        stt_backend=stt_backend,
        mlx_available=mlx_available,
        tts_backend=tts_backend,
        fallbacks=fallbacks,
        diagnostics=diagnostics,
    )


def _detect_tts_backend(
    pytorch_device: str, is_apple_silicon: bool
) -> str:
    """Determine TTS backend and whether it uses GPU."""
    if pytorch_device == "mps":
        return "piper-http-mps"  # Piper uses ONNX, not PyTorch
    if pytorch_device == "cuda":
        return "piper-http-cuda"
    if is_apple_silicon:
        return "piper-http-cpu"  # Piper ONNX on CPU (no Metal backend)
    return "piper-http-cpu"
