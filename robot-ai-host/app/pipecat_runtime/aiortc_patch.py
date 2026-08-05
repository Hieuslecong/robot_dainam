"""Patch aiortc background tasks to prevent unhandled Task exceptions when WebRTC connections close.

When a WebRTC peer connection or ICE transport closes abruptly (e.g., client disconnects or re-connects),
aiortc's internal background `__connect()` task raises `InvalidStateError("RTCIceTransport is closed")` or `ConnectionError`.
Since aiortc spawns `__connect()` via `asyncio.ensure_future()` without catching exceptions, this results in:
`[ERROR] asyncio: Task exception was never retrieved: InvalidStateError('RTCIceTransport is closed')`

This module safely patches `RTCPeerConnection.__connect` to catch closed-transport errors and log them at DEBUG
level rather than letting them bubble up as unhandled asyncio task exceptions.
"""

import logging
from typing import Any

logger = logging.getLogger("app.pipecat_runtime.aiortc_patch")

_patched = False


def apply_aiortc_patches() -> bool:
    """Apply safety patches to aiortc if installed."""
    global _patched
    if _patched:
        return True

    try:
        import aiortc.rtcpeerconnection
        from aiortc.exceptions import InvalidStateError
        from aiortc.rtcpeerconnection import RTCPeerConnection
    except ImportError:
        logger.debug("aiortc is not installed; skipping aiortc patches")
        return False

    orig_connect = getattr(RTCPeerConnection, "_RTCPeerConnection__connect", None)
    if orig_connect is None:
        logger.warning("Could not find _RTCPeerConnection__connect on RTCPeerConnection")
        return False

    async def safe_connect(self: Any) -> None:
        try:
            await orig_connect(self)
        except (InvalidStateError, ConnectionError, OSError) as exc:
            exc_str = str(exc).lower()
            conn_state = getattr(self, "connectionState", None)
            if "closed" in exc_str or conn_state in ("closed", "failed"):
                logger.debug(
                    "Handled expected aiortc connect state change on closed transport: %s (state=%s)",
                    exc,
                    conn_state,
                )
            else:
                logger.warning("aiortc RTCPeerConnection connect failed: %s", exc)

    setattr(RTCPeerConnection, "_RTCPeerConnection__connect", safe_connect)
    _patched = True
    logger.info("Successfully applied aiortc RTCPeerConnection background task patches")
    return True
