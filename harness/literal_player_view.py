import json
import time
from pathlib import Path


SCREEN_PATH = Path(
    r"P:\Astra-MM1\control\screen.json"
)

READ_ATTEMPTS = 20
READ_RETRY_DELAY = 0.01


def _read_screen_snapshot():
    last_error = None

    for _ in range(READ_ATTEMPTS):
        try:
            payload = json.loads(
                SCREEN_PATH.read_text(
                    encoding="utf-8"
                )
            )

            width = payload.get("width")
            height = payload.get("height")
            lines = payload.get("lines")

            if width != 40:
                raise RuntimeError(
                    "unexpected screen width"
                )

            if height != 25:
                raise RuntimeError(
                    "unexpected screen height"
                )

            if not isinstance(lines, list):
                raise RuntimeError(
                    "screen lines missing"
                )

            if len(lines) != height:
                raise RuntimeError(
                    "unexpected screen line count"
                )

            if not all(
                isinstance(line, str)
                for line in lines
            ):
                raise RuntimeError(
                    "invalid screen line"
                )

            return {
                "width": width,
                "height": height,
                "lines": lines,
            }

        except (
            FileNotFoundError,
            PermissionError,
            json.JSONDecodeError,
        ) as exc:
            last_error = exc
            time.sleep(READ_RETRY_DELAY)

    raise RuntimeError(
        "screen snapshot temporarily unavailable"
    ) from last_error


def build_player_view(engineering_state):
    # Engineering state remains internal and is deliberately
    # not included in the player-facing observation.
    return {
        "screen": _read_screen_snapshot(),
    }
