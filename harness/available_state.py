"""Player-facing AvailableState / PreviousStateContext assembly."""

from party_state import get_party_state
from text_state import get_current_text
from transition_context import get_previous_state_context
from geometry_state import get_visible_geometry


def get_available_state(
    memory: bytes,
    engineering_state: dict | None = None,
) -> dict:
    return {
        "party": get_party_state(memory),
        "text": get_current_text(),
        "visible_geometry": get_visible_geometry(engineering_state),
    }


def build_observation(
    memory: bytes,
    transition_events: list[dict] | None = None,
    engineering_state: dict | None = None,
) -> dict:
    return {
        "available_state": get_available_state(
            memory,
            engineering_state,
        ),
        "previous_state_context": get_previous_state_context(
            transition_events or []
        ),
    }
