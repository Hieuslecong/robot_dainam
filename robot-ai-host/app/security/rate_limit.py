"""Simple in-memory rate limiting for API endpoints.

Uses a sliding window with per-IP counters.
Not suitable for distributed deployments — use Redis in production.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter:
    """Per-key sliding-window rate limiter."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def _prune(self, key: str, now: float) -> None:
        cutoff = now - self.window_seconds
        self._buckets[key] = [t for t in self._buckets[key] if t > cutoff]

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        self._prune(key, now)
        if len(self._buckets[key]) >= self.max_requests:
            return False
        self._buckets[key].append(now)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply rate limits per-endpoint based on config."""

    # (path_prefix, method, max_requests, window_seconds)
    RULES: list[tuple[str, str, int, float]] = [
        ("/v1/devices/register", "POST", 100, 60),  # generous for test suites
        ("/v1/sessions", "POST", 100, 60),           # generous for test suites
        ("/v1/sessions/", "POST", 100, 60),           # generous for test suites
        ("/v1/admin", "POST", 20, 60),
        ("/v1/admin/knowledge", "POST", 10, 60),
        ("/v1/admin", "PUT", 20, 60),
    ]

    def __init__(self, app, *, get_client_ip: Callable[[Request], str] | None = None) -> None:
        super().__init__(app)
        self._limiters: dict[tuple[str, str], RateLimiter] = {}
        self._get_client_ip = get_client_ip or (lambda r: r.client.host if r.client else "unknown")
        for path, method, max_req, window in self.RULES:
            self._limiters[(path, method)] = RateLimiter(max_req, window)

    async def dispatch(self, request: Request, call_next):
        # Skip health check
        if request.url.path == "/health":
            return await call_next(request)

        # Find matching rule (longest prefix match)
        matched_limiter = None
        for (path, method), limiter in self._limiters.items():
            if request.url.path.startswith(path) and request.method == method:
                matched_limiter = limiter
                break

        if matched_limiter:
            client_ip = self._get_client_ip(request)
            key = f"{client_ip}:{request.url.path}:{request.method}"
            if not matched_limiter.is_allowed(key):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please wait before retrying."},
                )

        return await call_next(request)
