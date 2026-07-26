#!/usr/bin/env python3
"""Create/update .env for the local GLM OpenAI-compatible gateway.

The token is requested through getpass so it is not placed in shell history or
command-line arguments. The resulting .env is chmod 0600 and must remain
ignored by Git.
"""

from __future__ import annotations

import argparse
import getpass
import os
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ENV = ROOT_DIR / ".env"
TEMPLATE = ROOT_DIR / ".env.glm-local.example"

DEFAULTS = {
    "DEFAULT_PROFILE": "hybrid_local_vi",
    "LLM_BASE_URL": "http://127.0.0.1:20128/v1",
    "LLM_MODEL": "opencode-go/glm-5.1",
    "LLM_TIMEOUT_SECONDS": "60",
    "LLM_RETRY_ON_TIMEOUT": "true",
    "LLM_DEFAULT_HEADERS_JSON": "{}",
}

KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("LLM base URL must be an absolute HTTP(S) URL")
    return value.rstrip("/")


def _replace_or_append(lines: list[str], updates: dict[str, str]) -> list[str]:
    remaining = dict(updates)
    output: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            output.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in remaining:
            output.append(f"{key}={remaining.pop(key)}\n")
        else:
            output.append(line)
    if remaining:
        if output and output[-1].strip():
            output.append("\n")
        output.append("# Local GLM gateway preset\n")
        for key, value in remaining.items():
            output.append(f"{key}={value}\n")
    return output


def configure(
    *,
    env_file: Path,
    base_url: str,
    model: str,
    token: str | None,
    keep_existing_token: bool,
) -> None:
    base_url = _validate_url(base_url)
    if not model.strip():
        raise ValueError("LLM model must not be empty")

    if env_file.exists():
        lines = env_file.read_text(encoding="utf-8").splitlines(keepends=True)
    elif TEMPLATE.exists():
        lines = TEMPLATE.read_text(encoding="utf-8").splitlines(keepends=True)
    else:
        lines = []

    updates = dict(DEFAULTS)
    updates["LLM_BASE_URL"] = base_url
    updates["LLM_MODEL"] = model.strip()
    if not keep_existing_token:
        if not token or not token.strip():
            raise ValueError("LLM token must not be empty")
        if "\n" in token or "\r" in token:
            raise ValueError("LLM token contains an invalid newline")
        updates["LLM_API_KEY"] = token.strip()

    for key in updates:
        if not KEY_PATTERN.match(key):
            raise ValueError(f"Invalid environment key: {key}")

    env_file.write_text("".join(_replace_or_append(lines, updates)), encoding="utf-8")
    try:
        os.chmod(env_file, 0o600)
    except OSError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--base-url", default=DEFAULTS["LLM_BASE_URL"])
    parser.add_argument("--model", default=DEFAULTS["LLM_MODEL"])
    parser.add_argument(
        "--keep-existing-token",
        action="store_true",
        help="Update endpoint/model without prompting for or replacing LLM_API_KEY.",
    )
    args = parser.parse_args()

    token: str | None = None
    if not args.keep_existing_token:
        token = getpass.getpass("LLM API token (input hidden): ")

    try:
        configure(
            env_file=args.env_file,
            base_url=args.base_url,
            model=args.model,
            token=token,
            keep_existing_token=args.keep_existing_token,
        )
    except ValueError as exc:
        print(f"[FAIL] {exc}")
        return 2

    print(f"[PASS] Updated {args.env_file}")
    print(f"[PASS] LLM_BASE_URL={_validate_url(args.base_url)}")
    print(f"[PASS] LLM_MODEL={args.model}")
    print("[PASS] LLM_API_KEY stored locally (value hidden)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
