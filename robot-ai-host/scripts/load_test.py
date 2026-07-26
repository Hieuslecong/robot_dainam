#!/usr/bin/env python3
"""Four-device control-plane soak/load test.

This script validates registration, session isolation, heartbeat, metrics and
cleanup. It does NOT claim to be a WebRTC media load test; use four browser
contexts for the media/data-plane acceptance described in TESTING.md.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time

import httpx


async def register_and_create(client: httpx.AsyncClient, index: int, profile: str, provisioning_secret: str):
    device_id = f"load-device-{index}"
    register = await client.post(
        "/v1/devices/register",
        json={
            "device_id": device_id,
            "device_type": "load_test_control_plane",
            "provisioning_secret": provisioning_secret,
            "capabilities": {"audio_input": True, "audio_output": True},
        },
    )
    register.raise_for_status()
    token = register.json()["access_token"]
    session = await client.post(
        "/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={"device_id": device_id, "profile": profile},
    )
    session.raise_for_status()
    return device_id, token, session.json()["session_id"]


async def run(args) -> int:
    started = time.monotonic()
    async with httpx.AsyncClient(base_url=args.server, timeout=15) as client:
        sessions = await asyncio.gather(
            *(register_and_create(client, i + 1, args.profile, args.provisioning_secret) for i in range(args.clients))
        )
        if len({sid for _, _, sid in sessions}) != args.clients:
            raise RuntimeError("Session IDs are not unique")

        deadline = time.monotonic() + args.duration
        heartbeat_count = 0
        while time.monotonic() < deadline:
            responses = await asyncio.gather(
                *(
                    client.post(
                        f"/v1/sessions/{sid}/heartbeat",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    for _, token, sid in sessions
                )
            )
            for response in responses:
                response.raise_for_status()
            heartbeat_count += len(responses)
            await asyncio.sleep(min(args.heartbeat_interval, max(0.0, deadline - time.monotonic())))

        states = []
        for device_id, token, sid in sessions:
            response = await client.get(
                f"/v1/sessions/{sid}", headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            state = response.json()
            if state["device_id"] != device_id:
                raise RuntimeError(f"Ownership leakage for {sid}")
            states.append(state)

        for _, token, sid in sessions:
            response = await client.delete(
                f"/v1/sessions/{sid}", headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()

        metrics = (await client.get("/v1/metrics")).json()
        result = {
            "test_type": "control_plane_only",
            "clients": args.clients,
            "duration_s": round(time.monotonic() - started, 3),
            "heartbeat_requests": heartbeat_count,
            "unique_sessions": len({item["session_id"] for item in states}),
            "ownership_isolated": True,
            "metrics": metrics,
            "webrtc_media_tested": False,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    parser.add_argument("--clients", type=int, default=4)
    parser.add_argument("--duration", type=float, default=15)
    parser.add_argument("--heartbeat-interval", type=float, default=5)
    parser.add_argument("--profile", default="mock")
    parser.add_argument(
        "--provisioning-secret",
        default=os.environ.get("PROVISIONING_SECRET", "dev-provisioning-secret"),
    )
    args = parser.parse_args()
    if args.clients < 1 or args.clients > 4:
        parser.error("--clients must be between 1 and 4 for the MVP")
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
