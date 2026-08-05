"""Cloudflare TURN credential service — generates per-session short-lived TURN keys.

Calls Cloudflare's TURN credential API and returns ICE server configs.
Falls back to static ``WEBRTC_ICE_SERVERS`` when Cloudflare TURN is not configured.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

# ── Cloudflare TURN defaults ──────────────────────────────────────────────
CF_TURN_API = "https://rtc.live.cloudflare.com/v1/turn/keys"

# Static Cloudflare STUN server (always safe to include)
CF_STUN_SERVER = {"urls": "stun:stun.cloudflare.com:3478"}

# Cloudflare TURN server URLs for different transports
CF_TURN_URLS = {
    "udp": "turn:turn.cloudflare.com:3478?transport=udp",
    "tcp": "turn:turn.cloudflare.com:3478?transport=tcp",
    "tcp_80": "turn:turn.cloudflare.com:80?transport=tcp",
    "tls_5349": "turns:turn.cloudflare.com:5349?transport=tcp",
    "tls_443": "turns:turn.cloudflare.com:443?transport=tcp",
}


@dataclass
class TurnCredential:
    """A generated TURN credential with expiry."""
    username: str
    credential: str
    urls: list[str]
    ttl: int
    created_at: float = field(default_factory=time.monotonic)
    expires_at: float = field(default=0)

    def __post_init__(self) -> None:
        self.expires_at = self.created_at + self.ttl

    @property
    def expired(self) -> bool:
        return time.monotonic() > self.expires_at

    def seconds_remaining(self) -> float:
        return max(0, self.expires_at - time.monotonic())


class CloudflareTurnService:
    """Generates per-session TURN credentials from Cloudflare."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._configured = bool(
            settings.cloudflare_turn_key_id and settings.cloudflare_turn_api_token
        )
        if self._configured:
            logger.info(
                "cloudflare_turn_configured",
                key_id=settings.cloudflare_turn_key_id[:8] + "..." if settings.cloudflare_turn_key_id else "",
                ttl=settings.cloudflare_turn_ttl_seconds,
            )
        else:
            logger.info("cloudflare_turn_not_configured_fallback_static")

    @property
    def use_cloudflare(self) -> bool:
        return self._configured

    async def generate_credentials(self) -> TurnCredential | None:
        """Call Cloudflare API to generate short-lived TURN credentials.

        Returns None on failure (caller should fall back to static config).
        """
        if not self._configured:
            return None

        url = f"{CF_TURN_API}/{self._settings.cloudflare_turn_key_id}/credentials/generate"
        headers = {
            "Authorization": f"Bearer {self._settings.cloudflare_turn_api_token}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {"ttl": self._settings.cloudflare_turn_ttl_seconds}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=body, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error(
                "cloudflare_turn_api_failed",
                status=getattr(exc, "response", None) and exc.response.status_code,
                error=str(exc),
            )
            return None

        ice = data.get("iceServers", {})
        username = ice.get("username", "")
        credential = ice.get("credential", "")
        api_urls = ice.get("urls", [])

        if not username or not credential:
            logger.error("cloudflare_turn_credential_empty", response_keys=list(data.keys()))
            return None

        return TurnCredential(
            username=username,
            credential=credential,
            urls=api_urls if api_urls else list(CF_TURN_URLS.values()),
            ttl=self._settings.cloudflare_turn_ttl_seconds,
        )

    def build_ice_servers(
        self,
        credential: TurnCredential | None = None,
    ) -> list[dict[str, Any]]:
        """Build the ICE server list for a session.

        When Cloudflare TURN is available, returns CF STUN + CF TURN.
        Otherwise falls back to the static WEBRTC_ICE_SERVERS config.
        """
        servers: list[dict[str, Any]] = []

        if credential is not None:
            # ── Cloudflare path: CF STUN + CF TURN ───────────────────────
            if self._settings.webrtc_enable_stun:
                servers.append(CF_STUN_SERVER)
            urls: list[str] = []
            if self._settings.webrtc_enable_turn_udp:
                urls.append(CF_TURN_URLS["udp"])
            if self._settings.webrtc_enable_turn_tcp:
                urls.append(CF_TURN_URLS["tcp"])
                urls.append(CF_TURN_URLS["tcp_80"])
            if self._settings.webrtc_enable_turn_tls:
                urls.append(CF_TURN_URLS["tls_5349"])
                urls.append(CF_TURN_URLS["tls_443"])
            if urls:
                servers.append({
                    "urls": urls,
                    "username": credential.username,
                    "credential": credential.credential,
                })
        else:
            # ── Static fallback: parse WEBRTC_ICE_SERVERS once ──────────
            from app.pipecat_runtime.ice_utils import parse_ice_servers
            all_servers = parse_ice_servers(self._settings.webrtc_ice_servers)
            for s in all_servers:
                url = s.get("urls", "")
                is_stun = "stun" in str(url).lower()
                is_turn = "turn" in str(url).lower()
                if is_stun and not self._settings.webrtc_enable_stun:
                    continue
                if is_turn and not (
                    self._settings.webrtc_enable_turn_udp
                    or self._settings.webrtc_enable_turn_tcp
                    or self._settings.webrtc_enable_turn_tls
                ):
                    continue
                servers.append(s)

        # Force relay mode?
        if self._settings.webrtc_force_relay:
            servers = [s for s in servers
                       if "turn" in str(s.get("urls", s.get("url", ""))).lower()]

        return servers


# ── Module-level singleton ────────────────────────────────────────────────
_turn_service: CloudflareTurnService | None = None


def get_turn_service(settings: Settings | None = None) -> CloudflareTurnService:
    global _turn_service
    if _turn_service is None and settings is not None:
        _turn_service = CloudflareTurnService(settings)
    if _turn_service is None:
        from app.config import get_settings
        _turn_service = CloudflareTurnService(get_settings())
    return _turn_service
