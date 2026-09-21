"""Player-legal projection of MM1's current party records."""

from state import decode_runtime_party


def get_party_state(memory: bytes) -> list[dict]:
    result = []

    for member in decode_runtime_party(memory):
        projected = {
            "position": member["position"],
            "name": member["name"],
            "class": member["class"],
            "level": member["level"],
            "hp": dict(member["hp"]),
            "spell_points": dict(member["spell_points"]),
            "armor_class": member["armor_class"],
            "food": member["food"],
        }

        condition = member.get("condition")
        if condition and not condition.startswith("unknown_"):
            projected["condition"] = condition

        result.append(projected)

    return result
