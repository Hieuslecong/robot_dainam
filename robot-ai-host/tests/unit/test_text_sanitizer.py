import asyncio

from app.pipecat_runtime.text_filter import VietnameseSpeechTextFilter
from app.pipecat_runtime.text_sanitizer import (
    sanitize_spoken_vietnamese,
    strip_emotion_tags,
)
from app.pipecat_runtime.vieneu_engine import STYLE_MAP


def test_removes_code_markdown_and_long_url_without_damaging_vietnamese():
    text = "# Kết quả **đúng** 3.14. Xem [tài liệu](https://example.com/a). ```python\nprint('x')\n```"
    spoken = sanitize_spoken_vietnamese(text)
    assert spoken == "Kết quả đúng 3.14. Xem tài liệu."
    assert "python" not in spoken
    assert "https" not in spoken


def test_replaces_raw_url_and_keeps_diacritics():
    spoken = sanitize_spoken_vietnamese("Mở https://example.com để kiểm tra tiếng Việt.")
    assert spoken == "Mở liên kết để kiểm tra tiếng Việt."


def test_sanitize_keeps_vieneu_emotion_tags():
    # VieNeu renders [cười]/[thở dài] as real sounds — sanitize must not eat them.
    assert sanitize_spoken_vietnamese("[cười] Hay quá!") == "[cười] Hay quá!"


def test_strip_emotion_tags_removes_all_known_cues():
    text = "[cười] Vui ghê. [thở dài] Tiếc thật. [hắng giọng] Bắt đầu nhé."
    assert strip_emotion_tags(text) == "Vui ghê. Tiếc thật. Bắt đầu nhé."


def test_filter_strip_tags_flag_controls_emotion_tags():
    keep = asyncio.run(VietnameseSpeechTextFilter().filter("[cười] Chào bạn!"))
    strip = asyncio.run(
        VietnameseSpeechTextFilter(strip_tags=True).filter("[cười] Chào bạn!")
    )
    assert keep == "[cười] Chào bạn!"
    assert strip == "Chào bạn!"


def test_style_map_only_uses_styles_the_model_knows():
    # VieNeu v3 Turbo style_labels: anything else silently degrades to tu_nhien.
    assert set(STYLE_MAP.values()) <= {"tu_nhien", "tin_tuc", "doc_truyen"}


def test_list_numbering_stripped_so_aggregator_gets_no_bare_dots():
    text = "Bạn thử cách này: 1. Liệt kê việc cần làm. 2. Chọn hai việc gấp nhất. 10) Nghỉ ngơi."
    spoken = sanitize_spoken_vietnamese(text)
    assert spoken == "Bạn thử cách này: Liệt kê việc cần làm. Chọn hai việc gấp nhất. Nghỉ ngơi."


def test_year_number_not_treated_as_list_marker():
    assert sanitize_spoken_vietnamese("Năm 2026. Khóa 15 nhập học.") == "Năm 2026. Khóa 15 nhập học."


def test_speed_shift_shortens_audio_and_keeps_identity_at_1x():
    import numpy as np

    from app.pipecat_runtime.vieneu_engine import speed_shift

    wave = np.sin(np.linspace(0, 20, 48000)).astype(np.float32)
    assert speed_shift(wave, 1.0) is wave
    faster = speed_shift(wave, 1.08)
    assert abs(len(faster) - int(48000 / 1.08)) <= 1
