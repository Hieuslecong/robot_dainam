#!/usr/bin/env python3
"""AST-level compatibility checks against the vendored Pipecat v1.6.0 source."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "vendor" / "pipecat-reference" / "src" / "pipecat"


def class_node(path: Path, name: str) -> ast.ClassDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"Class {name} not found in {path}")


def method_args(cls: ast.ClassDef, method_name: str) -> set[str]:
    for node in cls.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name:
            names = {arg.arg for arg in [*node.args.args, *node.args.kwonlyargs]}
            if node.args.vararg:
                names.add(node.args.vararg.arg)
            if node.args.kwarg:
                names.add(node.args.kwarg.arg)
            return names
    raise AssertionError(f"Method {cls.name}.{method_name} not found")


def require_args(label: str, actual: set[str], expected: set[str]) -> None:
    missing = expected - actual
    if missing:
        raise AssertionError(f"{label} missing arguments: {sorted(missing)}")
    print(f"[PASS] {label}: {sorted(expected)}")


def main() -> int:
    manifest = ROOT / "vendor" / "pipecat-reference" / "UPSTREAM_COMMIT"
    assert manifest.read_text(encoding="utf-8").strip() == "08e871599904080cedad7ce5683676ab8481fa59"
    print("[PASS] upstream commit manifest")

    worker = class_node(SRC / "pipeline" / "worker.py", "PipelineWorker")
    require_args(
        "PipelineWorker.__init__",
        method_args(worker, "__init__"),
        {"pipeline", "params", "enable_rtvi", "observers", "name"},
    )

    runner = class_node(SRC / "workers" / "runner.py", "WorkerRunner")
    require_args("WorkerRunner.__init__", method_args(runner, "__init__"), {"handle_sigint"})
    require_args("WorkerRunner.add_workers", method_args(runner, "add_workers"), {"workers"})
    require_args("WorkerRunner.run", method_args(runner, "run"), {"auto_end"})
    require_args("WorkerRunner.cancel", method_args(runner, "cancel"), {"reason"})

    tts = class_node(SRC / "services" / "tts_service.py", "TTSService")
    require_args(
        "TTSService.__init__",
        method_args(tts, "__init__"),
        {"text_aggregation_mode", "text_filters", "settings", "sample_rate"},
    )

    handler = class_node(
        SRC / "transports" / "smallwebrtc" / "request_handler.py",
        "SmallWebRTCRequestHandler",
    )
    require_args(
        "SmallWebRTCRequestHandler.handle_web_request",
        method_args(handler, "handle_web_request"),
        {"request", "webrtc_connection_callback"},
    )
    require_args(
        "SmallWebRTCRequestHandler.handle_patch_request",
        method_args(handler, "handle_patch_request"),
        {"request"},
    )


    openai_base = class_node(SRC / "services" / "openai" / "base_llm.py", "BaseOpenAILLMService")
    require_args(
        "BaseOpenAILLMService.__init__",
        method_args(openai_base, "__init__"),
        {"api_key", "base_url", "default_headers", "retry_timeout_secs", "retry_on_timeout", "settings"},
    )

    piper = class_node(SRC / "services" / "piper" / "tts.py", "PiperHttpTTSService")
    require_args(
        "PiperHttpTTSService.__init__",
        method_args(piper, "__init__"),
        {"base_url", "aiohttp_session", "settings"},
    )

    whisper = class_node(SRC / "services" / "whisper" / "stt.py", "WhisperSTTService")
    require_args(
        "WhisperSTTService.__init__",
        method_args(whisper, "__init__"),
        {"device", "compute_type", "settings"},
    )

    whisper_mlx = class_node(SRC / "services" / "whisper" / "stt.py", "WhisperSTTServiceMLX")
    require_args(
        "WhisperSTTServiceMLX.__init__",
        method_args(whisper_mlx, "__init__"),
        {"settings"},
    )

    rtvi = class_node(SRC / "processors" / "frameworks" / "rtvi" / "processor.py", "RTVIProcessor")
    require_args("RTVIProcessor.send_server_message", method_args(rtvi, "send_server_message"), {"data"})
    require_args("RTVIProcessor.send_error_response", method_args(rtvi, "send_error_response"), {"client_msg", "error"})

    print("ALL VENDORED PIPECAT SOURCE CONTRACT CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
