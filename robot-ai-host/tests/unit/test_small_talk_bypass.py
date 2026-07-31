"""Heuristic small-talk bypass — canned replies without touching the LLM."""

from app.processors.small_talk_bypass import match_small_talk

NAME = "Mây Mây"


def _match(text):
    return match_small_talk(text, persona_name=NAME)


def test_greetings_bypass():
    for text in ["xin chào", "Chào bạn!", "hello", "alo"]:
        assert _match(text) is not None, text


def test_name_question_returns_persona_name():
    for text in ["bạn tên gì?", "bạn là ai", "bạn là ai vậy", "vậy bạn là ai đó", "cho mình hỏi bạn là ai"]:
        reply = _match(text)
        assert reply is not None and NAME in reply, text



def test_thanks_and_goodbye_bypass():
    assert _match("cảm ơn bạn nha") is not None
    assert _match("tạm biệt nhé") is not None


def test_real_questions_go_to_llm():
    for text in [
        "chào bạn, cho mình hỏi học phí kỳ này",  # school topic
        "thư viện mở cửa mấy giờ",
        "giải thích giúp mình định luật Newton",
        "chào cờ thứ mấy",  # starts like a greeting but is a question
        "mình bị bắt nạt ở lớp",  # safety signal must reach the LLM
    ]:
        assert _match(text) is None, text


def test_long_utterances_never_bypass():
    assert _match("xin chào bạn ơi hôm nay mình muốn hỏi một chuyện") is None
