"""Normalize one boundary-to-boundary player-visible event slice."""


def get_previous_state_context(events: list[dict]) -> list[dict]:
    context = []

    for event in events:
        if event.get("type") != "lower_text":
            continue

        lines = event.get("lines")
        if not isinstance(lines, list):
            continue

        context.append({
            "type": "lower_text",
            "lines": [
                line
                for line in lines
                if isinstance(line, str)
            ],
        })

    return context
