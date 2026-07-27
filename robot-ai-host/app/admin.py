"""Admin API — runtime settings, knowledge, and server management.

Endpoints:
  GET  /v1/admin/settings          — read all editable settings
  PUT  /v1/admin/settings          — update settings (writes .env + live reload)
  GET  /v1/admin/voices            — list available VieNeu voices
  POST /v1/admin/knowledge/upload  — upload a knowledge file
  GET  /v1/admin/knowledge         — list knowledge files
  DELETE /v1/admin/knowledge/{name} — delete a knowledge file
  POST /v1/admin/restart           — restart the server
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.auth import get_current_device
from app.config import get_settings as _cfg_get_settings

router = APIRouter(prefix="/v1/admin", tags=["admin"])

# ── Editable settings (whitelist) ──────────────────────────────────────────
_EDITABLE_KEYS = {
    "TTS": [
        "VIENEU_VOICE",
        "VIENEU_SPEED",
        "VIENEU_STYLE",
        "VIENEU_TEMPERATURE",
    ],
    "LLM": [
        "LLM_MODEL",
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "LLM_TEMPERATURE",
        "LLM_MAX_TOKENS",
    ],
    "STT": [
        "STT_CANDIDATE",
    ],
    "SYSTEM": [
        "MAX_SESSIONS",
        "LOCAL_STT_MAX_SESSIONS",
        "HEARTBEAT_TIMEOUT_SECONDS",
    ],
}

_ALL_EDITABLE = [k for group in _EDITABLE_KEYS.values() for k in group]

# ── Voice list ──────────────────────────────────────────────────────────────
_KNOWN_VIENEU_VOICES = [
    "Đoan Trang",
    "Anh Thư",
    "Thanh Hà",
    "Minh Quân",
    "Ngọc Lan",
    "Hoàng Nam",
]

# ── Knowledge directory ────────────────────────────────────────────────────
_KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"


def _read_env() -> dict[str, str]:
    """Parse .env file into a dict."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    result: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


def _write_env(updates: dict[str, str]) -> None:
    """Write key-value pairs back to .env, preserving comments and order."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        raise FileNotFoundError(".env not found")
    lines = env_path.read_text(encoding="utf-8").splitlines()
    updated_keys = set(updates.keys())
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in updated_keys:
            new_lines.append(f"{key}={updates[key]}")
            updated_keys.discard(key)
        else:
            new_lines.append(line)

    # Append new keys at the end
    for key in updated_keys:
        new_lines.append(f"{key}={updates[key]}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


# ── Routes ──────────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings(request: Request, _device: dict[str, Any] = __import__("fastapi").Depends(get_current_device)):
    """Return all editable settings with their current values."""
    env = _read_env()
    settings = _cfg_get_settings()
    result: dict[str, dict[str, Any]] = {}

    for group, keys in _EDITABLE_KEYS.items():
        items = {}
        for key in keys:
            items[key] = {
                "value": env.get(key, getattr(settings, key.lower(), "")),
                "editable": True,
            }
        result[group] = items

    return result


@router.put("/settings")
async def update_settings(
    request: Request,
    body: dict[str, Any],
    _device: dict[str, Any] = __import__("fastapi").Depends(get_current_device),
):
    """Update editable settings. Only whitelisted keys are accepted."""
    updates: dict[str, str] = {}
    for group, keys in _EDITABLE_KEYS.items():
        if group in body and isinstance(body[group], dict):
            for key in keys:
                if key in body[group]:
                    updates[key] = str(body[group][key])

    if not updates:
        raise HTTPException(status_code=400, detail="No valid settings provided")

    unknown = set(updates) - set(_ALL_EDITABLE)
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown keys: {unknown}")

    _write_env(updates)

    return {"status": "ok", "updated": list(updates.keys())}


@router.get("/voices")
async def list_voices(_device: dict[str, Any] = __import__("fastapi").Depends(get_current_device)):
    """List available TTS voices."""
    return {"voices": _KNOWN_VIENEU_VOICES}


@router.get("/knowledge")
async def list_knowledge(_device: dict[str, Any] = __import__("fastapi").Depends(get_current_device)):
    """List all knowledge files."""
    _KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, Any]] = []
    for f in sorted(_KNOWLEDGE_DIR.rglob("*")):
        if f.is_file() and not f.name.startswith("."):
            files.append({
                "name": str(f.relative_to(_KNOWLEDGE_DIR)),
                "size": f.stat().st_size,
            })
    return {"files": files}


@router.post("/knowledge/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    _device: dict[str, Any] = __import__("fastapi").Depends(get_current_device),
):
    """Upload a knowledge file (max 10 MB, .yaml/.yml/.txt/.md only)."""
    _MAX_BYTES = 10 * 1024 * 1024
    _ALLOWED = {".yaml", ".yml", ".txt", ".md"}
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in _ALLOWED:
        raise HTTPException(status_code=400, detail=f"File type '{suffix}' not allowed. Use: {', '.join(sorted(_ALLOWED))}")
    _KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    dest = _KNOWLEDGE_DIR / file.filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    if dest.stat().st_size > _MAX_BYTES:
        dest.unlink()
        raise HTTPException(status_code=413, detail=f"File exceeds {_MAX_BYTES // (1024*1024)} MB limit")
    return {"status": "ok", "name": file.filename, "size": dest.stat().st_size}


@router.delete("/knowledge/{name:path}")
async def delete_knowledge(
    name: str,
    _device: dict[str, Any] = __import__("fastapi").Depends(get_current_device),
):
    """Delete a knowledge file."""
    target = _KNOWLEDGE_DIR / name
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not str(target.resolve()).startswith(str(_KNOWLEDGE_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Path traversal denied")
    target.unlink()
    return {"status": "deleted", "name": name}


@router.post("/restart")
async def restart_server(
    _device: dict[str, Any] = __import__("fastapi").Depends(get_current_device),
):
    """Restart the server by exiting (process manager should restart it)."""
    import signal

    os.kill(os.getpid(), signal.SIGTERM)
    return {"status": "restarting"}
