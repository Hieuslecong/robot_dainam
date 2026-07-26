from pathlib import Path

from scripts.configure_glm_local import configure

ROOT = Path(__file__).resolve().parents[2]


def test_glm_example_contains_endpoint_and_model_without_real_token():
    text = (ROOT / ".env.glm-local.example").read_text(encoding="utf-8")
    assert "LLM_BASE_URL=http://127.0.0.1:20128/v1" in text
    assert "LLM_MODEL=opencode-go/glm-5.1" in text
    assert "LLM_API_KEY=replace-with-token" in text
    assert "sk-" not in text


def test_configure_glm_writes_preset_and_secret_without_printing_it(tmp_path):
    env_file = tmp_path / ".env"
    configure(
        env_file=env_file,
        base_url="http://localhost:20128/v1/",
        model="opencode-go/glm-5.1",
        token="test-secret-token",
        keep_existing_token=False,
    )
    text = env_file.read_text(encoding="utf-8")
    assert "DEFAULT_PROFILE=hybrid_local_vi" in text
    assert "LLM_BASE_URL=http://localhost:20128/v1" in text
    assert "LLM_MODEL=opencode-go/glm-5.1" in text
    assert "LLM_API_KEY=test-secret-token" in text


def test_check_script_supports_nonstream_and_sse_without_token_literal():
    text = (ROOT / "scripts" / "check_llm_endpoint.py").read_text(encoding="utf-8")
    assert '"stream": streaming' in text
    assert 'line.startswith("data:")' in text
    assert "resolved_llm_api_key" in text
    assert "sk-" not in text


def test_run_script_checks_endpoint_before_starting_host():
    text = (ROOT / "scripts" / "run_glm_local_hybrid.sh").read_text(encoding="utf-8")
    assert "scripts/check_llm_endpoint.py" in text
    assert "scripts/check_hybrid_profile.py" in text
    assert "-m app.main --profile hybrid_local_vi" in text


def test_local_test_orchestrator_and_prompt_are_present():
    orchestrator = (ROOT / "scripts" / "test_glm_local_project.sh").read_text(encoding="utf-8")
    prompt = (ROOT / "PROMPT_TEST_GLM_LOCAL.md").read_text(encoding="utf-8")
    assert "scripts/check_llm_endpoint.py" in orchestrator
    assert "npm run build" in orchestrator
    assert "http://127.0.0.1:20128/v1" in prompt
    assert "opencode-go/glm-5.1" in prompt
    assert "LLM_API_KEY=<token thật>" not in prompt
