#!/usr/bin/env python3
"""Probe an OpenAI-compatible LLM endpoint without exposing its API token."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import Settings


def _headers(settings: Settings) -> dict[str, str]:
    headers = {"Content-Type": "application/json", **settings.llm_default_headers}
    if settings.resolved_llm_api_key and "Authorization" not in headers:
        headers["Authorization"] = f"Bearer {settings.resolved_llm_api_key}"
    return headers


def _safe_detail(response: httpx.Response, limit: int = 600) -> str:
    text = response.text.replace("\n", " ").strip()
    return text[:limit]


def _extract_content(payload: dict) -> str:
    try:
        message = payload["choices"][0]["message"]
        content = message.get("content") or message.get("reasoning_content") or ""
        return str(content).strip()
    except (KeyError, IndexError, TypeError, AttributeError):
        return ""


def check_models(client: httpx.Client, base_url: str) -> tuple[bool, str]:
    response = client.get(f"{base_url}/models")
    if response.status_code == 404:
        return True, "not implemented (HTTP 404); continuing with chat probe"
    if response.is_error:
        return False, f"HTTP {response.status_code}: {_safe_detail(response)}"
    try:
        payload = response.json()
    except ValueError:
        return False, "response is not JSON"
    count = len(payload.get("data", [])) if isinstance(payload, dict) else 0
    return True, f"reachable; model entries={count}"


def check_chat(
    client: httpx.Client, base_url: str, model: str, *, streaming: bool
) -> tuple[bool, str, float]:
    request = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Chỉ trả lời đúng một từ: OK"}
        ],
        "stream": streaming,
    }
    started = time.perf_counter()

    if not streaming:
        response = client.post(f"{base_url}/chat/completions", json=request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        if response.is_error:
            return False, f"HTTP {response.status_code}: {_safe_detail(response)}", elapsed_ms
        try:
            payload = response.json()
        except ValueError:
            return False, "response is not JSON", elapsed_ms
        content = _extract_content(payload)
        if not content:
            return False, "missing choices[0].message.content", elapsed_ms
        return True, f"response={content[:160]!r}", elapsed_ms

    event_count = 0
    saw_done = False
    first_event_ms: float | None = None
    with client.stream("POST", f"{base_url}/chat/completions", json=request) as response:
        if response.is_error:
            body = response.read().decode(errors="replace")[:600]
            elapsed_ms = (time.perf_counter() - started) * 1000
            return False, f"HTTP {response.status_code}: {body}", elapsed_ms
        for line in response.iter_lines():
            if not line:
                continue
            if not line.startswith("data:"):
                continue
            if first_event_ms is None:
                first_event_ms = (time.perf_counter() - started) * 1000
            data = line[5:].strip()
            if data == "[DONE]":
                saw_done = True
                break
            try:
                json.loads(data)
            except json.JSONDecodeError:
                return False, "stream contains invalid JSON SSE data", first_event_ms or 0.0
            event_count += 1

    elapsed_ms = (time.perf_counter() - started) * 1000
    if event_count == 0:
        return False, "no SSE data events received", elapsed_ms
    detail = f"SSE events={event_count}, done={saw_done}, first_event_ms={first_event_ms:.1f}"
    return True, detail, elapsed_ms


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-models", action="store_true")
    parser.add_argument("--skip-stream", action="store_true")
    parser.add_argument("--timeout", type=float, default=None)
    args = parser.parse_args()

    settings = Settings()
    base_url = settings.resolved_llm_base_url
    model = settings.resolved_llm_model
    if not base_url:
        print("[FAIL] LLM_BASE_URL is empty")
        return 2
    if not settings.resolved_llm_api_key:
        print("[FAIL] LLM_API_KEY is empty")
        return 2
    if not model:
        print("[FAIL] LLM_MODEL is empty")
        return 2

    timeout = args.timeout or settings.llm_timeout_seconds
    try:
        with httpx.Client(headers=_headers(settings), timeout=timeout) as client:
            if not args.skip_models:
                ok, detail = check_models(client, base_url)
                print(f"[{'PASS' if ok else 'FAIL'}] GET /models: {detail}")
                if not ok:
                    return 3

            ok, detail, elapsed = check_chat(client, base_url, model, streaming=False)
            print(f"[{'PASS' if ok else 'FAIL'}] chat non-stream: {detail}; total_ms={elapsed:.1f}")
            if not ok:
                return 4

            if not args.skip_stream:
                ok, detail, elapsed = check_chat(client, base_url, model, streaming=True)
                print(f"[{'PASS' if ok else 'FAIL'}] chat stream: {detail}; total_ms={elapsed:.1f}")
                if not ok:
                    return 5
    except httpx.ConnectError as exc:
        print(f"[FAIL] Cannot connect to {base_url}: {exc}")
        print("[HINT] Confirm the local gateway is listening on TCP port 20128.")
        return 6
    except httpx.TimeoutException:
        print(f"[FAIL] Endpoint timed out after {timeout} seconds")
        return 7
    except ValueError as exc:
        print(f"[FAIL] Configuration error: {exc}")
        return 8

    print(f"[PASS] endpoint={base_url}")
    print(f"[PASS] model={model}")
    print("[PASS] token accepted (value intentionally hidden)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
