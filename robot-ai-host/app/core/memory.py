"""Consent-gated long-term preference memory (spec 13.3–13.5).

- Nothing is stored without explicit consent per item.
- Only allowlisted preference kinds may be stored (13.3).
- Sensitive categories are refused outright (13.5).
- Users can view, delete one, delete all, or disable storage (13.4).
- Storage is per-user JSON files; user isolation is structural (one file per
  user id) so cross-user leakage is impossible by construction.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from app.logging_utils import get_logger

logger = get_logger(__name__)

MEMORY_DIR = Path("artifacts/memory")

ALLOWED_KINDS = (
    "preferred_name",
    "address_style",
    "preferred_voice",
    "accessibility",
    "frequent_schedule",
)

# Spec 13.5 — refuse to store these even with consent.
_FORBIDDEN_PATTERNS = re.compile(
    r"(password|mật khẩu|api[_ ]?key|token|thẻ tín dụng|credit card|số tài khoản|"
    r"bệnh|thuốc|chẩn đoán|hiv|ung thư|thu nhập|lương)",
    re.IGNORECASE,
)


class MemoryRefused(ValueError):
    pass


class MemoryStore:
    def __init__(self, directory: Path | None = None) -> None:
        self._dir = directory or MEMORY_DIR

    def _path(self, user_id: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", user_id)
        return self._dir / f"{safe}.json"

    def _load(self, user_id: str) -> dict:
        path = self._path(user_id)
        if not path.exists():
            return {"disabled": False, "items": {}}
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, user_id: str, data: dict) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path(user_id).write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    # -- writes ---------------------------------------------------------------

    def remember(self, user_id: str, kind: str, value: str, *, consent: bool) -> dict:
        if not consent:
            raise MemoryRefused("Chỉ lưu sau khi người dùng đồng ý (spec 13.3).")
        if kind not in ALLOWED_KINDS:
            raise MemoryRefused(f"Loại '{kind}' không thuộc allowlist preference.")
        if _FORBIDDEN_PATTERNS.search(value):
            raise MemoryRefused("Nội dung thuộc nhóm cấm lưu (spec 13.5).")
        data = self._load(user_id)
        if data.get("disabled"):
            raise MemoryRefused("Người dùng đã tắt lưu memory.")
        data["items"][kind] = {
            "value": value,
            "stored_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self._save(user_id, data)
        logger.info("memory_stored", user_id=user_id, kind=kind)
        return data["items"][kind]

    # -- control (spec 13.4) --------------------------------------------------

    def view(self, user_id: str) -> dict:
        data = self._load(user_id)
        return {"disabled": data.get("disabled", False), "items": data.get("items", {})}

    def delete_one(self, user_id: str, kind: str) -> bool:
        data = self._load(user_id)
        removed = data["items"].pop(kind, None) is not None
        self._save(user_id, data)
        return removed

    def delete_all(self, user_id: str) -> None:
        data = self._load(user_id)
        data["items"] = {}
        self._save(user_id, data)

    def set_disabled(self, user_id: str, disabled: bool) -> None:
        data = self._load(user_id)
        data["disabled"] = disabled
        if disabled:
            data["items"] = {}  # disabling also clears stored items
        self._save(user_id, data)
