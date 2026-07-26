"""Glossary correction tests (spec 8.3)."""

from pathlib import Path

import pytest

from app.core.glossary import GlossaryCorrector

GLOSSARY = Path(__file__).resolve().parents[2] / "config" / "glossary.yaml"


@pytest.fixture(scope="module")
def corrector() -> GlossaryCorrector:
    return GlossaryCorrector(GLOSSARY)


def test_exact_variant_corrected(corrector):
    result = corrector.correct("cho mình hỏi về tính chỉ học kỳ này")
    assert "tín chỉ" in result.text
    assert result.corrections
    assert result.corrections[0].confidence == 1.0


def test_correction_keeps_original(corrector):
    result = corrector.correct("phòng đạo tạo ở đâu")
    assert "Phòng Đào tạo" in result.text
    assert "đạo tạo" in result.corrections[0].original


def test_clean_text_untouched(corrector):
    text = "hôm nay trời đẹp quá"
    result = corrector.correct(text)
    assert result.text == text
    assert not result.corrections


def test_low_confidence_not_applied(corrector):
    # Nothing in the glossary is close to this — must never "correct" it.
    text = "xin chào các bạn sinh viên"
    result = corrector.correct(text)
    assert result.text == text


def test_glossary_versioned(corrector):
    assert corrector.version >= 1
    assert 0.0 < corrector.threshold <= 1.0
