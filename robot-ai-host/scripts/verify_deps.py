#!/usr/bin/env python3
"""Verify the exact Pipecat baseline and reject deprecated project imports."""

from __future__ import annotations

import importlib
import importlib.metadata
import re
import subprocess
import sys
from pathlib import Path

EXPECTED_VERSION = "1.6.0"
EXPECTED_COMMIT = "08e871599904080cedad7ce5683676ab8481fa59"
DEPRECATED_PATTERNS = {
    "PipelineTask": re.compile(r"\bPipelineTask\b"),
    "PipelineRunner": re.compile(r"\bPipelineRunner\b"),
    "aggregate_sentences": re.compile(r"\baggregate_sentences\s*="),
}


def result(label: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    return ok


def reference_commit(ref_path: Path) -> tuple[str, str]:
    git_dir = ref_path / ".git"
    if git_dir.exists():
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ref_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip(), "git"
    manifest = ref_path / "UPSTREAM_COMMIT"
    if manifest.is_file():
        return manifest.read_text(encoding="utf-8").strip(), "manifest"
    return "", "unavailable"


def scan_deprecated(root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted((root / "app").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for label, pattern in DEPRECATED_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(root)}: {label}")
    return findings


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    failures = 0

    try:
        version = importlib.metadata.version("pipecat-ai")
        failures += not result(
            "pipecat-ai package version", version == EXPECTED_VERSION, f"got {version}"
        )
    except importlib.metadata.PackageNotFoundError:
        result("pipecat-ai package version", False, "package is not installed")
        failures += 1

    ref_path = root / "vendor" / "pipecat-reference"
    commit, source = reference_commit(ref_path)
    failures += not result(
        "Pipecat reference commit",
        commit == EXPECTED_COMMIT,
        f"source={source}, got={commit or 'none'}",
    )

    imports = [
        ("pipecat.pipeline.worker", "PipelineWorker"),
        ("pipecat.workers.runner", "WorkerRunner"),
        ("pipecat.pipeline.pipeline", "Pipeline"),
        ("pipecat.transports.smallwebrtc.transport", "SmallWebRTCTransport"),
        ("pipecat.processors.frameworks.rtvi", "RTVIProcessor"),
        ("pipecat.audio.vad.silero", "SileroVADAnalyzer"),
    ]
    for module_name, symbol in imports:
        try:
            module = importlib.import_module(module_name)
            getattr(module, symbol)
            result(f"Public import {module_name}.{symbol}", True)
        except Exception as exc:  # Dependency/import failures are reportable here.
            result(f"Public import {module_name}.{symbol}", False, repr(exc))
            failures += 1

    findings = scan_deprecated(root)
    failures += not result(
        "No deprecated Pipecat API in app source",
        not findings,
        "; ".join(findings) if findings else "source scan clean",
    )

    lock_text = (root / "uv.lock").read_text(encoding="utf-8") if (root / "uv.lock").exists() else ""
    failures += not result(
        "uv.lock pins Pipecat 1.6.0",
        'name = "pipecat-ai"' in lock_text and 'version = "1.6.0"' in lock_text,
    )

    print("=" * 64)
    if failures:
        print(f"FAILED: {int(failures)} verification check(s) failed")
        return 1
    print("ALL VERIFICATION CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
