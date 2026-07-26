"""Knowledge retrieval + read-only school tools tests (spec 12, 11.1)."""

import asyncio

import pytest

from app.core.knowledge import KnowledgeStore
from app.tools.gateway import ToolGateway
from app.tools import school_tools
from app.tools.school_tools import register_school_tools


@pytest.fixture
def gateway(tmp_path):
    gw = ToolGateway(audit_path=tmp_path / "audit.jsonl")
    register_school_tools(gw)
    return gw


def test_all_five_read_only_tools_registered(gateway):
    assert set(gateway.names) == {
        "search_school_knowledge",
        "get_school_schedule",
        "find_school_form",
        "get_deadline",
        "get_contact_information",
    }


def test_search_returns_evidence_with_source(gateway):
    result = asyncio.run(
        gateway.execute("search_school_knowledge", {"query": "thư viện ở đâu"})
    )
    assert result.status == "success"
    hit = result.data["results"][0]
    for key in ("evidence", "source_title", "source_version", "effective_date",
                "relevance_score", "retrieval_timestamp"):
        assert key in hit
    assert "thư viện" in hit["evidence"].lower()


def test_no_match_never_invents_source(gateway):
    result = asyncio.run(
        gateway.execute("search_school_knowledge", {"query": "zzz không tồn tại xyzabc"})
    )
    assert result.status == "partial"
    assert result.data["results"] == []
    assert "Không tìm thấy" in result.message


def test_deadline_lookup(gateway):
    result = asyncio.run(gateway.execute("get_deadline", {"query": "hạn đăng ký học phần"}))
    assert result.status == "success"
    assert any("25/08" in r["evidence"] for r in result.data["results"])


def test_contact_lookup(gateway):
    result = asyncio.run(
        gateway.execute("get_contact_information", {"query": "liên hệ phòng đào tạo"})
    )
    assert result.status == "success"
    assert any("daotao@" in r["evidence"] for r in result.data["results"])


def test_expired_document_warns(tmp_path):
    doc = tmp_path / "old.yaml"
    doc.write_text(
        """
source_id: old-001
title: "Tài liệu cũ"
version: "0.9"
effective_date: "2020-01-01"
expiry_date: "2021-01-01"
issuing_unit: "Test"
document_type: general
entries:
  - text: "Nội dung quy định cũ về học phí."
    keywords: [học phí, quy định]
""",
        encoding="utf-8",
    )
    store = KnowledgeStore(tmp_path)
    hits = store.search("quy định học phí")
    assert hits and hits[0].stale_warning is not None


def test_doc_without_required_metadata_rejected(tmp_path):
    (tmp_path / "bad.yaml").write_text("title: thiếu metadata\nentries: []", encoding="utf-8")
    store = KnowledgeStore(tmp_path)
    assert store.search("thiếu") == []
