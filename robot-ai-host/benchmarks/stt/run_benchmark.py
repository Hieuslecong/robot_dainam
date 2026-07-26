"""Round-1 STT benchmark on the public VIVOS test set (spec 23.1, round 1).

Ranks the five candidates in config/stt_candidates.yaml on WER/CER,
per-utterance transcription latency and process RSS. Round 1 is a preliminary
ranking on public data only — it can eliminate weak candidates but must NOT be
used to declare the default (that needs the round-2 self-recorded corpus).

Usage:
    .venv-hybrid/bin/python benchmarks/stt/run_benchmark.py \
        --limit 100 --candidates stt_fast_vi stt_balanced_vi ...

Outputs:
    artifacts/upgrade/stt_round1.json   (raw per-candidate results)
    artifacts/upgrade/stt_round1.md     (ranking table)
"""

from __future__ import annotations

import argparse
import gc
import json
import re
import tarfile
import time
import unicodedata
from pathlib import Path

import psutil
import yaml

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES_PATH = ROOT / "config" / "stt_candidates.yaml"
OUT_DIR = ROOT / "artifacts" / "upgrade"
VIVOS_TAR_NAME = "vivos.tar.gz"


def normalize(text: str) -> str:
    """VIVOS ground truth is uppercase, unpunctuated. Normalize both sides."""
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"[^\w\sàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def find_vivos_tar() -> Path:
    from huggingface_hub import snapshot_download

    snap = snapshot_download("AILAB-VNUHCM/vivos", repo_type="dataset")
    tar = Path(snap) / "data" / VIVOS_TAR_NAME
    if not tar.exists():
        raise FileNotFoundError(f"VIVOS tarball missing: {tar}")
    return tar


def extract_test_set(tar_path: Path, work_dir: Path) -> list[tuple[Path, str]]:
    """Extract VIVOS test wavs + prompts; return [(wav_path, ground_truth)]."""
    extracted = work_dir / "vivos"
    if not (extracted / "test" / "prompts.txt").exists():
        with tarfile.open(tar_path) as tar:
            members = [m for m in tar.getmembers() if m.name.startswith("vivos/test/")]
            tar.extractall(work_dir, members=members, filter="data")
    prompts_file = extracted / "test" / "prompts.txt"
    pairs: list[tuple[Path, str]] = []
    for line in prompts_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        utt_id, text = line.split(" ", 1)
        speaker = utt_id.split("_")[0]
        wav = extracted / "test" / "waves" / speaker / f"{utt_id}.wav"
        if wav.exists():
            pairs.append((wav, text))
    return pairs


def _ensure_real_weights(repo: str) -> None:
    """Guard against LFS-pointer-only snapshots (76-byte 'model.safetensors')."""
    from huggingface_hub import snapshot_download

    snap = Path(snapshot_download(repo))
    weights = list(snap.glob("*.safetensors")) + list(snap.glob("*.npz")) + list(snap.rglob("*.onnx"))
    if weights and all(w.stat().st_size < 1_000_000 for w in weights):
        print(f"  ! {repo}: weights are LFS pointers — forcing re-download")
        snapshot_download(repo, force_download=True)


class MlxEngine:
    def __init__(self, model: str) -> None:
        import mlx_whisper  # noqa: F401

        _ensure_real_weights(model)
        self.model = model

    def transcribe(self, wav: Path) -> str:
        import mlx_whisper

        result = mlx_whisper.transcribe(
            str(wav), path_or_hf_repo=self.model, language="vi", temperature=0.0
        )
        return result["text"]


class FasterWhisperEngine:
    def __init__(self, model: str) -> None:
        from faster_whisper import WhisperModel

        _ensure_real_weights(model)
        self._model = WhisperModel(model, device="cpu", compute_type="int8")

    def transcribe(self, wav: Path) -> str:
        segments, _ = self._model.transcribe(str(wav), language="vi", temperature=0.0)
        return " ".join(segment.text for segment in segments)


class SherpaEngine:
    def __init__(self, model_repo: str) -> None:
        import sherpa_onnx
        from huggingface_hub import snapshot_download

        snap = Path(snapshot_download(model_repo))
        tokens = next(snap.rglob("tokens.txt"))
        encoder = next(snap.rglob("encoder*.onnx"))
        decoder = next(snap.rglob("decoder*.onnx"))
        joiner = next(snap.rglob("joiner*.onnx"))
        self._recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            tokens=str(tokens),
            encoder=str(encoder),
            decoder=str(decoder),
            joiner=str(joiner),
            num_threads=4,
        )

    def transcribe(self, wav: Path) -> str:
        import soundfile as sf

        audio, sample_rate = sf.read(wav, dtype="float32")
        stream = self._recognizer.create_stream()
        stream.accept_waveform(sample_rate, audio)
        self._recognizer.decode_stream(stream)
        return stream.result.text


ENGINES = {"mlx": MlxEngine, "faster_whisper": FasterWhisperEngine, "sherpa_onnx": SherpaEngine}


def run_candidate(name: str, spec: dict, pairs: list[tuple[Path, str]]) -> dict:
    import jiwer

    process = psutil.Process()
    rss_before = process.memory_info().rss
    load_start = time.monotonic()
    engine = ENGINES[spec["engine"]](spec["model"])
    load_seconds = time.monotonic() - load_start

    references: list[str] = []
    hypotheses: list[str] = []
    latencies: list[float] = []
    peak_rss = process.memory_info().rss
    for wav, truth in pairs:
        started = time.monotonic()
        try:
            hypothesis = engine.transcribe(wav)
        except Exception as exc:  # record, don't die mid-run
            hypothesis = ""
            print(f"  ! {name} failed on {wav.name}: {exc}")
        latencies.append(time.monotonic() - started)
        references.append(normalize(truth))
        hypotheses.append(normalize(hypothesis))
        peak_rss = max(peak_rss, process.memory_info().rss)

    empty = sum(1 for h in hypotheses if not h)
    if empty > len(pairs) * 0.5:
        return {
            "candidate": name, "engine": spec["engine"], "model": spec["model"],
            "error": f"{empty}/{len(pairs)} empty transcriptions — engine/weights broken, WER not comparable",
        }

    wer = jiwer.wer(references, hypotheses)
    cer = jiwer.cer(references, hypotheses)
    latencies.sort()
    del engine
    gc.collect()
    return {
        "candidate": name,
        "engine": spec["engine"],
        "model": spec["model"],
        "utterances": len(pairs),
        "wer": round(wer, 4),
        "cer": round(cer, 4),
        "latency_p50_s": round(latencies[len(latencies) // 2], 3),
        "latency_p90_s": round(latencies[int(len(latencies) * 0.9)], 3),
        "model_load_s": round(load_seconds, 2),
        "rss_delta_mb": round((peak_rss - rss_before) / 1e6, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100, help="utterance cap (round-1 ranking subset)")
    parser.add_argument("--candidates", nargs="*", default=None)
    args = parser.parse_args()

    candidates: dict = yaml.safe_load(CANDIDATES_PATH.read_text(encoding="utf-8"))
    selected = args.candidates or list(candidates)

    work_dir = OUT_DIR / "vivos-work"
    work_dir.mkdir(parents=True, exist_ok=True)
    pairs = extract_test_set(find_vivos_tar(), work_dir)
    total = len(pairs)
    pairs = pairs[: args.limit]
    print(f"VIVOS test set: {total} utterances, benchmarking on {len(pairs)} (--limit {args.limit})")

    results = []
    for name in selected:
        spec = candidates[name]
        print(f"== {name} ({spec['model']})")
        try:
            result = run_candidate(name, spec, pairs)
        except Exception as exc:
            result = {"candidate": name, "engine": spec["engine"], "model": spec["model"], "error": str(exc)}
        print("  ", result)
        results.append(result)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "corpus": "VIVOS test (public, round 1 — preliminary ranking only, not default-selection evidence)",
        "subset": f"{len(pairs)}/{total} utterances",
        "results": results,
    }
    (OUT_DIR / "stt_round1.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    ok = [r for r in results if "error" not in r]
    ok.sort(key=lambda r: r["wer"])
    lines = [
        "# STT Round-1 Benchmark — VIVOS test (public corpus)",
        "",
        f"Subset: {len(pairs)}/{total} utterances (capped for round-1 ranking; cap logged, not hidden).",
        "Round 1 chỉ xếp hạng sơ bộ — KHÔNG đủ chốt mặc định (cần corpus vòng 2, spec 23.1).",
        "",
        "| Candidate | Engine | WER | CER | Lat P50 (s) | Lat P90 (s) | Load (s) | RSS Δ (MB) |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in ok:
        lines.append(
            f"| {r['candidate']} | {r['engine']} | {r['wer']:.4f} | {r['cer']:.4f} "
            f"| {r['latency_p50_s']} | {r['latency_p90_s']} | {r['model_load_s']} | {r['rss_delta_mb']} |"
        )
    for r in results:
        if "error" in r:
            lines.append(f"| {r['candidate']} | {r['engine']} | ERROR: {r['error'][:80]} | | | | | |")
    (OUT_DIR / "stt_round1.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote", OUT_DIR / "stt_round1.json", "and stt_round1.md")


if __name__ == "__main__":
    main()
