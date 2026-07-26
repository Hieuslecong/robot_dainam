"""Versioned glossary correction for Vietnamese STT output (spec 8.3).

Corrections keep the original transcript, the corrected transcript and a
confidence score. Low-confidence matches are never applied.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.logging_utils import get_logger

logger = get_logger(__name__)

DEFAULT_GLOSSARY_PATH = Path(__file__).resolve().parents[2] / "config" / "glossary.yaml"


@dataclass
class Correction:
    original: str
    corrected: str
    confidence: float


@dataclass
class GlossaryResult:
    text: str
    corrections: list[Correction] = field(default_factory=list)


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text).lower().strip()


class GlossaryCorrector:
    """Phrase-level exact and fuzzy matching against a versioned glossary."""

    def __init__(self, path: Path | None = None) -> None:
        raw = yaml.safe_load((path or DEFAULT_GLOSSARY_PATH).read_text(encoding="utf-8"))
        self.version: int = raw.get("version", 0)
        self.threshold: float = float(raw.get("confidence_threshold", 0.8))
        # variant (normalized) → canonical
        self._exact: dict[str, str] = {}
        for canonical, variants in (raw.get("terms") or {}).items():
            for variant in variants or []:
                self._exact[_norm(variant)] = canonical
        # sorted longest-first so multi-word phrases win over subphrases
        self._variants = sorted(self._exact, key=len, reverse=True)

    def correct(self, text: str) -> GlossaryResult:
        result = GlossaryResult(text=text)
        if not text.strip() or not self._variants:
            return result

        corrected = unicodedata.normalize("NFC", text)
        for variant in self._variants:
            canonical = self._exact[variant]
            pattern = re.compile(re.escape(variant), re.IGNORECASE)
            new_text = pattern.sub(canonical, corrected)
            if new_text != corrected:
                result.corrections.append(
                    Correction(original=corrected, corrected=new_text, confidence=1.0)
                )
                corrected = new_text

        # Fuzzy pass: single unknown phrases close to a variant.
        if not result.corrections:
            norm = _norm(corrected)
            match = difflib.get_close_matches(norm, self._variants, n=1, cutoff=self.threshold)
            if match:
                ratio = difflib.SequenceMatcher(None, norm, match[0]).ratio()
                if ratio >= self.threshold:
                    canonical = self._exact[match[0]]
                    result.corrections.append(
                        Correction(original=corrected, corrected=canonical, confidence=round(ratio, 3))
                    )
                    corrected = canonical

        if result.corrections:
            for c in result.corrections:
                logger.info(
                    "glossary_correction",
                    original=c.original,
                    corrected=c.corrected,
                    confidence=c.confidence,
                    glossary_version=self.version,
                )
        result.text = corrected
        return result
