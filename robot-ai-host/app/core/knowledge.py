"""Source-aware school knowledge retrieval (spec 12).

Documents live in ``knowledge/school/*.yaml`` with mandatory source metadata
(spec 12.2). Retrieval returns evidence WITH source title/version/effective
date (spec 12.4); expired or undated documents trigger a staleness warning.
No document ⇒ no answer — sources are never invented.
"""

from __future__ import annotations

import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.logging_utils import get_logger

logger = get_logger(__name__)

KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge" / "school"

REQUIRED_METADATA = ("source_id", "title", "version", "effective_date", "issuing_unit")


@dataclass
class KnowledgeHit:
    answer_evidence: str
    source_title: str
    source_version: str
    effective_date: str
    relevance_score: float
    retrieval_timestamp: str
    stale_warning: str | None = None
    extra: dict = field(default_factory=dict)


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text).lower()


class KnowledgeStore:
    def __init__(self, directory: Path | None = None) -> None:
        self._dir = directory or KNOWLEDGE_DIR
        self._docs: list[dict] = []
        self.reload()

    def reload(self) -> None:
        self._docs = []
        if not self._dir.exists():
            logger.warning("knowledge_dir_missing", path=str(self._dir))
            return
        for path in sorted(self._dir.glob("*.yaml")):
            try:
                doc = yaml.safe_load(path.read_text(encoding="utf-8"))
                missing = [k for k in REQUIRED_METADATA if not doc.get(k)]
                if missing:
                    logger.warning(
                        "knowledge_doc_rejected", path=path.name, missing=missing
                    )
                    continue
                self._docs.append(doc)
            except Exception as exc:
                logger.warning("knowledge_doc_unreadable", path=path.name, error=str(exc))

    def search(self, query: str, *, limit: int = 3, doc_type: str | None = None) -> list[KnowledgeHit]:
        terms = [t for t in _norm(query).split() if len(t) > 1]
        if not terms:
            return []
        hits: list[tuple[float, dict, dict]] = []
        for doc in self._docs:
            if doc_type and doc.get("document_type") != doc_type:
                continue
            for entry in doc.get("entries", []):
                haystack = _norm(entry.get("text", "") + " " + " ".join(entry.get("keywords", [])))
                score = sum(1.0 for t in terms if t in haystack) / len(terms)
                # Below half the query terms = noise, not evidence; returning
                # weak hits would let the agent cite irrelevant sources.
                if score >= 0.5:
                    hits.append((score, doc, entry))
        hits.sort(key=lambda item: item[0], reverse=True)

        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        results = []
        for score, doc, entry in hits[:limit]:
            warning = None
            expiry = doc.get("expiry_date")
            if expiry and str(expiry) < time.strftime("%Y-%m-%d"):
                warning = f"Tài liệu đã hết hiệu lực từ {expiry} — thông tin có thể cũ."
            elif not doc.get("effective_date"):
                warning = "Tài liệu không ghi ngày hiệu lực — thông tin có thể cũ."
            results.append(
                KnowledgeHit(
                    answer_evidence=entry.get("text", ""),
                    source_title=doc["title"],
                    source_version=str(doc["version"]),
                    effective_date=str(doc["effective_date"]),
                    relevance_score=round(score, 3),
                    retrieval_timestamp=now,
                    stale_warning=warning,
                    extra={k: entry[k] for k in entry if k not in ("text", "keywords")},
                )
            )
        return results
