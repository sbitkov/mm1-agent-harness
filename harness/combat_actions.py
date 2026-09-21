from __future__ import annotations


# DS:38B4..38B7
#
# Runtime-confirmed as the four visible dynamic combat-command markers:
# F / S / C / A.
#
# DS physical base for this binary is 0x189F0:
#     0x189F0 + 0x38B4 = 0x1C2A4
COMMAND_MARKERS_ADDR = 0x1C2A4
COMMAND_MARKER_NAMES = ("fight", "shoot", "cast", "attack")

# Runtime-confirmed in the shoot capture.
# Contains the visible upper enemy-group letter, e.g. ord("E").
TARGET_MAX_ADDR = 0x1BB8A


def decode_command_markers(data: bytes) -> set[str]:
    enabled = set()

    raw = data[
        COMMAND_MARKERS_ADDR:
        COMMAND_MARKERS_ADDR + 4
    ]

    for value, expected_letter, name in zip(
        raw,
        b"FSCA",
        COMMAND_MARKER_NAMES,
    ):
        if value == expected_letter:
            enabled.add(name)

    return enabled


def decode_enemy_targets(data: bytes) -> list[str]:
    target_max = data[TARGET_MAX_ADDR]

    if not ord("A") <= target_max <= ord("Z"):
        return []

    return [
        chr(value)
        for value in range(ord("A"), target_max + 1)
    ]


def build_combat_available_actions(
    mode: str,
    data: bytes,
    party: list[dict],
) -> dict:
    positions = [
        character["position"]
        for character in party
    ]

    if mode == "encounter_choice":
        return {
            "attack": True,
            "bribe": True,
            "retreat": True,
            "surrender": True,
        }

    if mode == "combat_command":
        dynamic = decode_command_markers(data)

        actions = {
            "delay": True,
            "protect": True,
            "quick_reference": True,
            "retreat": True,
            "use": True,
            "block": True,
            "view_party_character": positions,
        }

        if len(positions) > 1:
            actions["exchange"] = True

        for name in ("fight", "shoot", "cast", "attack"):
            if name in dynamic:
                actions[name] = True

        return actions

    if mode == "combat_exchange_target":
        return {
            "select_exchange_target": positions,
            "go_back": True,
        }

    if mode == "combat_shoot_target":
        return {
            "select_enemy_group": decode_enemy_targets(data),
            "go_back": True,
        }

    if mode == "combat_quickref":
        return {
            "view_party_character": positions,
            "go_back": True,
        }

    # Unknown/resolution states intentionally expose no input.
    return {}