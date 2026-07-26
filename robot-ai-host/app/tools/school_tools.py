"""Read-only school tools (spec 11.1) backed by the source-aware knowledge store."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.knowledge import KnowledgeStore
from app.tools.gateway import ToolGateway, ToolSpec

_store: KnowledgeStore | None = None


def _knowledge() -> KnowledgeStore:
    global _store
    if _store is None:
        _store = KnowledgeStore()
    return _store


def _hits_payload(hits) -> dict:
    if not hits:
        # Spec: no document ⇒ say so; never invent a source.
        return {
            "_status": "partial",
            "_message": "Không tìm thấy tài liệu phù hợp trong knowledge base.",
            "results": [],
        }
    return {
        "results": [
            {
                "evidence": h.answer_evidence,
                "source_title": h.source_title,
                "source_version": h.source_version,
                "effective_date": h.effective_date,
                "relevance_score": h.relevance_score,
                "retrieval_timestamp": h.retrieval_timestamp,
                "stale_warning": h.stale_warning,
                **h.extra,
            }
            for h in hits
        ]
    }


class QueryInput(BaseModel):
    query: str = Field(min_length=2, max_length=300)


async def search_school_knowledge(args: QueryInput) -> dict:
    return _hits_payload(_knowledge().search(args.query))


async def get_school_schedule(args: QueryInput) -> dict:
    return _hits_payload(_knowledge().search(args.query, doc_type="schedule"))


async def find_school_form(args: QueryInput) -> dict:
    return _hits_payload(_knowledge().search(args.query, doc_type="form"))


async def get_deadline(args: QueryInput) -> dict:
    hits = _knowledge().search(args.query, doc_type="schedule")
    hits = [h for h in hits if "hạn" in h.answer_evidence.lower() or h.extra.get("date")]
    return _hits_payload(hits)


async def get_contact_information(args: QueryInput) -> dict:
    return _hits_payload(_knowledge().search(args.query, doc_type="contact"))


def register_school_tools(gateway: ToolGateway) -> None:
    for name, handler in (
        ("search_school_knowledge", search_school_knowledge),
        ("get_school_schedule", get_school_schedule),
        ("find_school_form", find_school_form),
        ("get_deadline", get_deadline),
        ("get_contact_information", get_contact_information),
    ):
        gateway.register(
            ToolSpec(name=name, input_model=QueryInput, handler=handler, timeout_s=5.0)
        )
