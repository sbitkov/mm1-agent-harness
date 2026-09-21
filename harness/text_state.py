"""Fallible current-text provider backed by screen.json."""

from literal_player_view import _read_screen_snapshot


def get_current_text() -> dict:
    snapshot = _read_screen_snapshot()
    return {"current": list(snapshot["lines"])}


def get_text_provider_diagnostics() -> dict:
    return {
        "source": "screen.json",
        "freshness": "unverified_text_mirror",
    }
