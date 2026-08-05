"""Shared ICE server utilities — avoids circular imports between main and turn_credentials."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse


def parse_ice_servers(raw: str) -> list[dict[str, str]]:
    """Parse WEBRTC_ICE_SERVERS into list of {urls, username?, credential?}.

    Accepts two formats:
      - Plain URL: ``stun:host:port`` → ``{"urls": "stun:host:port"}``
      - URL with credential params: ``turn:host:port?transport=udp&username=x&credential=y``
        → ``{"urls": "turn:host:port?transport=udp", "username": "x", "credential": "y"}``
    """
    import re

    result: list[dict[str, str]] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        parsed = urlparse(item)
        qs = parse_qs(parsed.query)
        entry: dict[str, str] = {}
        base_url = item
        username = qs.get("username", [None])[0]
        credential = qs.get("credential", [None])[0]
        if username and credential:
            # Strip username/credential from URL query
            base_url = re.sub(r"[&?]username=[^&]*", "", base_url)
            base_url = re.sub(r"[&?]credential=[^&]*", "", base_url)
            entry["username"] = username
            entry["credential"] = credential
        entry["urls"] = base_url
        result.append(entry)
    return result
