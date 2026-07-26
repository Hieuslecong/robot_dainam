"""Structured logging facade with a stdlib fallback.

Production installs use structlog from ``pyproject.toml``. The fallback keeps
configuration/audit tests runnable in restricted offline environments where the
optional runtime dependency has not been installed yet.
"""

from __future__ import annotations

import json
import logging
from typing import Any


class _StdlibBoundLogger:
    def __init__(self, name: str | None = None) -> None:
        self._logger = logging.getLogger(name)

    def _log(self, level: int, event: str, **kwargs: Any) -> None:
        payload = f" {json.dumps(kwargs, ensure_ascii=False, default=str)}" if kwargs else ""
        self._logger.log(level, "%s%s", event, payload)

    def debug(self, event: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        self._log(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, event, **kwargs)

    warn = warning

    def error(self, event: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, event, **kwargs)

    def exception(self, event: str, **kwargs: Any) -> None:
        kwargs.setdefault("exc_info", True)
        self._log(logging.ERROR, event, **kwargs)


def get_logger(name: str | None = None):
    try:
        import structlog

        return structlog.get_logger(name)
    except ModuleNotFoundError:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        return _StdlibBoundLogger(name)
