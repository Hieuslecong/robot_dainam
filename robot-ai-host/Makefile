.PHONY: install frontend-install frontend-test frontend-build test run run-cloud verify cloud-check \
	hybrid-install-mac hybrid-install-linux hybrid-check hybrid-piper hybrid-run \
	glm-config glm-check glm-run load-test docker-build clean

install:
	uv sync --frozen

frontend-install:
	npm ci --prefix clients/browser

frontend-test:
	npm run test --prefix clients/browser

frontend-build:
	npm run build --prefix clients/browser

test:
	uv run pytest -q

run:
	uv run python -m app.main --profile mock

run-cloud:
	uv run python -m app.main --profile google_vi

verify:
	uv run python scripts/verify_deps.py

cloud-check:
	uv run python scripts/check_cloud_profile.py --profile google_vi

hybrid-install-mac:
	./scripts/install_hybrid_macos.sh

hybrid-install-linux:
	./scripts/install_hybrid_linux.sh

hybrid-check:
	.venv-hybrid/bin/python scripts/check_hybrid_profile.py --profile hybrid_local_vi

hybrid-piper:
	./scripts/run_piper.sh

hybrid-run:
	./scripts/run_hybrid_host.sh

load-test:
	uv run python scripts/load_test.py --clients 4 --duration 15

docker-build:
	docker build --no-cache -t robot-ai-host:fixed .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache clients/browser/node_modules clients/browser/dist


glm-config:
	.venv-hybrid/bin/python scripts/configure_glm_local.py

glm-check:
	.venv-hybrid/bin/python scripts/check_llm_endpoint.py

glm-run:
	./scripts/run_glm_local_hybrid.sh


glm-test:
	./scripts/test_glm_local_project.sh


# Phase 1 voice-quality evidence targets.
bench-stt:
	.venv-hybrid/bin/python benchmarks/stt/run_benchmark.py --limit 100 --candidates stt_balanced_vi stt_accurate_vi stt_research_vi stt_streaming_vi

bench-stt-all:
	.venv-hybrid/bin/python benchmarks/stt/run_benchmark.py --limit 100

tts-smoke:
	.venv-hybrid/bin/python benchmarks/tts/vieneu_smoke.py
