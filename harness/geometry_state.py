"""Player-visible exploration geometry from MM1 renderer decisions."""

import json
from pathlib import Path


GEOMETRY_PATH = Path(
    r"P:\Astra-MM1\control\visible_geometry.raw.json"
)

MAX_FORWARD_DEPTH = 3
_VISIBLE_STATES = {"open", "wall", "not_visible"}
_FIELDS = (
    "left",
    "left_front",
    "front",
    "right_front",
    "right",
)


def _read_payload(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def get_visible_geometry(
    engineering_state: dict | None,
    path: Path = GEOMETRY_PATH,
) -> dict | None:
    """Return only geometry that MM1's viewport renderer actually emitted.

    The raw sidecar is an engineering trace of already-resolved renderer
    branches. It is available only while the engineering state says that the
    exploration viewport remains player-visible, even if the broader UI mode
    is an unclassified exploration-preserving substate.
    """

    if (
        not isinstance(engineering_state, dict)
        or engineering_state.get("exploration_view_active") is not True
    ):
        return None

    payload = _read_payload(path)
    if payload is None:
        return None

    visibility = payload.get("visibility")
    if visibility == "suppressed":
        return {
            "visibility": "suppressed",
            "max_forward_depth": MAX_FORWARD_DEPTH,
            "layers": [],
        }

    if visibility != "visible":
        return None

    raw_layers = payload.get("internal_depths")
    if not isinstance(raw_layers, list):
        return None

    layers = []
    seen_depths = set()

    for raw in raw_layers:
        if not isinstance(raw, dict):
            return None

        depth = raw.get("internal_depth")
        if (
            not isinstance(depth, int)
            or isinstance(depth, bool)
            or not 0 <= depth <= MAX_FORWARD_DEPTH
            or depth in seen_depths
        ):
            return None

        layer = {"depth": depth}
        for field in _FIELDS:
            value = raw.get(field)
            if value not in _VISIBLE_STATES:
                return None
            layer[field] = value

        seen_depths.add(depth)
        layers.append(layer)

    layers.sort(key=lambda item: item["depth"])

    # A visible redraw always evaluates the current-cell layer. Refuse a
    # partial or torn sidecar instead of converting missing data into "open".
    if not layers or layers[0]["depth"] != 0:
        return None

    # Rendering terminates at the first front wall. A gap would therefore be
    # a corrupt trace rather than an occluded/open layer.
    if [item["depth"] for item in layers] != list(range(len(layers))):
        return None

    return {
        "visibility": "visible",
        "max_forward_depth": MAX_FORWARD_DEPTH,
        "layers": layers,
    }
