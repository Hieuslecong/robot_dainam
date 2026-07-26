"""Persona prompt tests — spec 9.4–9.5."""

from app.core.system_prompt import FALLBACK_PERSONA_NAME, build_system_prompt


def test_persona_name_comes_from_config_not_source():
    prompt = build_system_prompt(persona_name="N.E.K.O")
    assert "N.E.K.O" in prompt
    # Name must not be hard-coded anywhere in the builder module.
    import inspect

    import app.core.system_prompt as module

    assert "N.E.K.O" not in inspect.getsource(module)


def test_persona_fallback_name_when_unconfigured():
    prompt = build_system_prompt(profile={"assistant_name": ""})
    assert FALLBACK_PERSONA_NAME in prompt


def test_no_administrative_boilerplate():
    prompt = build_system_prompt()
    for line in prompt.splitlines():
        if "sẵn sàng hỗ trợ" in line.lower():
            # allowed only as an explicit prohibition, never as self-description
            assert "không" in line.lower()


def test_persona_style_rules_present():
    prompt = build_system_prompt(persona_name="Test")
    assert "mình" in prompt and "bạn" in prompt  # xưng hô mình – bạn
    assert "ấm áp" in prompt
    assert "không giả là con người" in prompt.lower()


def test_model_name_never_leaks_into_prompt():
    # Robot must not reveal the core model in conversation; the builder must
    # not embed it even when callers pass it in.
    prompt = build_system_prompt(persona_name="Test", llm_model="gemini-2.5-flash")
    assert "gemini" not in prompt.lower()
    assert "không tiết lộ model" in prompt.lower()


def test_face_commands_are_affirmed_not_refused():
    prompt = build_system_prompt(persona_name="Test")
    assert "khuôn mặt" in prompt.lower()
    assert "làm mặt buồn" in prompt.lower()


def test_prompt_within_token_budget():
    """Spec 9.7: core persona/safety 500–800 tokens. Vietnamese ~1.5 token/word
    heuristic; assert a generous word ceiling instead of exact tokens."""
    prompt = build_system_prompt(persona_name="Test", llm_model="test-model")
    words = len(prompt.split())
    assert words < 550, f"core prompt too long: {words} words"
