"""Stable MM1 input-boundary synchronization (engineering-only)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from live_state import ACTIVE_WAIT_PATH, read_active_wait


DEFAULT_TIMEOUT = 10.0
POLL_INTERVAL = 0.01


class WaitBoundaryError(RuntimeError):
    pass


def require_wait_seq(active_wait: dict | None) -> int:
    if active_wait is None:
        raise WaitBoundaryError(
            "MM1 active input boundary is unavailable"
        )

    wait_seq = active_wait.get("wait_seq")

    if wait_seq is None:
        raise WaitBoundaryError(
            "DOSBox-X instrumentation does not publish wait_seq; "
            "rebuild and restart the instrumented emulator"
        )

    return int(wait_seq)


def _read_active_wait_path(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        value = payload.get("return_ip")
        wait_seq = payload.get("wait_seq")

        if not isinstance(value, str):
            return None

        if (
            not isinstance(wait_seq, int)
            or isinstance(wait_seq, bool)
            or wait_seq < 0
        ):
            return None

        return {
            "return_ip": int(value, 16),
            "wait_seq": wait_seq,
        }
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def wait_for_next_boundary(
    previous_wait_seq: int,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    poll_interval: float = POLL_INTERVAL,
    path: Path = ACTIVE_WAIT_PATH,
) -> dict:
    deadline = time.monotonic() + timeout
    last_seen = None

    while time.monotonic() < deadline:
        active_wait = (
            read_active_wait()
            if path == ACTIVE_WAIT_PATH
            else _read_active_wait_path(path)
        )

        if active_wait is not None:
            last_seen = active_wait.get("wait_seq")

            if (
                isinstance(last_seen, int)
                and last_seen > previous_wait_seq
            ):
                return active_wait

        time.sleep(poll_interval)

    raise WaitBoundaryError(
        "timed out waiting for MM1 input boundary: "
        f"previous wait_seq={previous_wait_seq}, "
        f"last seen={last_seen!r}, timeout={timeout:.2f}s"
    )
