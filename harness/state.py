from pathlib import Path
import json
import sys

from combat_state import classify_combat_state, inspect_combat_primitives
from combat_actions import build_combat_available_actions


# ----------------------------------------------------------------------
# MM1 runtime structures discovered experimentally
# ----------------------------------------------------------------------

STATS_EFFECTIVE_ADDR = 0x1AD8B
STATS_BASE_ADDR = 0x1AD92

CLASS_ADDR = 0x1AD99
RACE_ADDR = 0x1AD9A
ALIGNMENT_ADDR = 0x1AD9B
SEX_ADDR = 0x1AD9C

NAME_ADDR = 0x1AD9D
NAME_LENGTH = 15

TOTAL_ADDR = 0x1ADAC
CLASS_FLAGS_ADDR = 0x1ADAD


# ----------------------------------------------------------------------
# Current UI handler signature.
#
# This appears to be a 16-bit pointer/address related to the currently
# active MM1 UI handler. It is used only internally for screen detection.
# It is never exposed to the agent.
# ----------------------------------------------------------------------

UI_SIGNATURE_ADDR = 0x289D6

UI_MAIN_MENU = 0x520B

UI_CHARACTER_CLASS = 0x531B
UI_CHARACTER_RACE = 0x546E
UI_CHARACTER_ALIGNMENT = 0x559D
UI_CHARACTER_SEX = 0x5660
UI_CHARACTER_NAME = 0x5737
UI_CHARACTER_SAVE_CONFIRMATION = 0x57AC

UI_CHARACTER_ROSTER = 0x5E79
UI_INN_SORPIGAL = 0x6276
UI_EXPLORATION = 0x4CDC
UI_EXPLORATION_SEARCH_RESULT = 0x4A1C

# Engineering-only ownership of the adventure viewport. Keep this list
# evidence-based: a wait belongs here only when MM1 leaves the exploration
# viewport, including its geometry, visibly active.
EXPLORATION_VIEW_WAIT_IPS = frozenset({
    UI_EXPLORATION,
    UI_EXPLORATION_SEARCH_RESULT,
})
CHARACTER_SHEET_FLAG_ADDR = 0x289B0
CHARACTER_SHEET_AUX_ADDR = 0x289B1
CHARACTER_SHEET_FLAG_OPEN = 0x01
CHARACTER_SHEET_AUX_OPEN = 0x00

PARTY_ADDR = 0x1AD85
PARTY_SIZE = 6
PARTY_EMPTY = 0xFF

RUNTIME_PARTY_BASE = 0x1CFEC
RUNTIME_PARTY_STRIDE = 0x80
RUNTIME_PARTY_COUNT = 6


# ----------------------------------------------------------------------
# Character roster
# ----------------------------------------------------------------------

ROSTER_BASE = 0x1C6EA
ROSTER_STRIDE = 0x7F
ROSTER_COUNT = 18
ROSTER_NAME_LENGTH = 16
ROSTER_CLASS_OFFSET = 0x14

# DS:45E8 вЂ” 18 metadata/location bytes, one per physical roster record.
ROSTER_META_BASE = 0x1CFD8

# DS:3BBC вЂ” current viewall/town filter value.
ROSTER_FILTER_ADDR = 0x1C5AC


STAT_NAMES = [
    "intellect",
    "might",
    "personality",
    "endurance",
    "speed",
    "accuracy",
    "luck",
]

CLASS_NAMES = {
    1: "knight",
    2: "paladin",
    3: "archer",
    4: "cleric",
    5: "sorcerer",
    6: "robber",
}

RACE_NAMES = {
    1: "human",
    2: "elf",
    3: "dwarf",
    4: "gnome",
    5: "half_orc",
}

ALIGNMENT_NAMES = {
    1: "good",
    2: "neutral",
    3: "evil",
}

SEX_NAMES = {
    1: "male",
    2: "female",
}

CLASS_AVAILABLE_MARKER = 0x17


def read_u16_le(data, addr):
    return data[addr] | (data[addr + 1] << 8)


def read_u24_le(data, addr):
    return (
        data[addr]
        | (data[addr + 1] << 8)
        | (data[addr + 2] << 16)
    )


def read_ascii_field(data, addr, length):
    raw = bytes(data[addr:addr + length])

    return raw.split(b"\x00", 1)[0].decode(
        "ascii",
        errors="replace",
    )


def decode_runtime_party(data):
    party = []

    for index in range(RUNTIME_PARTY_COUNT):
        base = (
            RUNTIME_PARTY_BASE
            + index * RUNTIME_PARTY_STRIDE
        )

        name = read_ascii_field(
            data,
            base,
            ROSTER_NAME_LENGTH,
        )

        if not name:
            continue

        class_id = data[
            base + ROSTER_CLASS_OFFSET
        ]

        stats = {
            "intellect": data[base + 0x15],
            "might": data[base + 0x17],
            "personality": data[base + 0x19],
            "endurance": data[base + 0x1B],
            "speed": data[base + 0x1D],
            "accuracy": data[base + 0x1F],
            "luck": data[base + 0x21],
        }

        level = data[base + 0x23]
        age = data[base + 0x25]

        experience = int.from_bytes(
            data[base + 0x27:base + 0x2B],
            "little",
        )

        spell_points_current = read_u16_le(
            data,
            base + 0x2B,
        )

        spell_points_maximum = read_u16_le(
            data,
            base + 0x2D,
        )

        gems = read_u24_le(
            data,
            base + 0x30,
        )

        gold = read_u24_le(
            data,
            base + 0x39,
        )

        hp_current = read_u16_le(
            data,
            base + 0x33,
        )

        hp_maximum = read_u16_le(
            data,
            base + 0x35,
        )

        armor_class = data[base + 0x3D]

        condition_id = data[base + 0x40]

        condition = (
            "good"
            if condition_id == 0x01
            else f"unknown_{condition_id:02X}"
        )

        food = read_u16_le(
            data,
            base + 0x3E,
        )

        party.append({
            "position": index + 1,
            "name": name,
            "class": CLASS_NAMES.get(
                class_id,
                f"unknown_{class_id}",
            ),
            "level": level,
            "age": age,
            "experience": experience,
            "spell_points": {
                "current": spell_points_current,
                "maximum": spell_points_maximum,
            },
            "gems": gems,
            "gold": gold,
            "hp": {
                "current": hp_current,
                "maximum": hp_maximum,
            },
            "armor_class": armor_class,
            "condition": condition,
            "food": food,
            "stats": stats,
        })

    return party

def decode_roster_with_mapping(data):
    """
    Decode the roster exactly as MM1 presents it to the player.

    Physical saved-record indices are engineering-only.  The UI letters
    A..N are dense ordinals over records whose metadata matches the
    current viewall/town filter.
    """
    characters = []
    by_physical_index = {}

    filter_value = data[ROSTER_FILTER_ADDR]

    for physical_index in range(ROSTER_COUNT):
        if data[ROSTER_META_BASE + physical_index] != filter_value:
            continue

        base = (
            ROSTER_BASE
            + physical_index * ROSTER_STRIDE
        )

        name = read_ascii_field(
            data,
            base,
            ROSTER_NAME_LENGTH,
        )

        # Metadata is the game's primary filter, but retaining this
        # sanity check prevents an invalid/empty record from leaking
        # into normalized state if a capture is inconsistent.
        if not name:
            continue

        class_id = data[
            base + ROSTER_CLASS_OFFSET
        ]

        # Display slots are dense ordinals, not physical indices.
        slot = chr(
            ord("A") + len(characters)
        )

        character = {
            "slot": slot,
            "name": name,
            "class": CLASS_NAMES.get(
                class_id,
                f"unknown_{class_id}",
            ),
        }

        characters.append(character)

        # Engineering-only map used to interpret PARTY_ADDR.
        # physical_index itself is never exposed to Astra-player.
        by_physical_index[physical_index] = character

    return characters, by_physical_index


def decode_roster(data):
    characters, _ = decode_roster_with_mapping(data)
    return characters


def decode_party(data, roster_by_physical_index):
    """
    PARTY_ADDR stores zero-based physical saved-roster indices.

    The displayed roster letters are reconstructed through the current
    filtered roster mapping rather than derived from physical indices.
    """
    party = []

    raw = data[
        PARTY_ADDR:
        PARTY_ADDR + PARTY_SIZE
    ]

    for position, physical_index in enumerate(raw, start=1):
        if physical_index == PARTY_EMPTY:
            continue

        if physical_index >= ROSTER_COUNT:
            continue

        character = roster_by_physical_index.get(
            physical_index
        )

        entry = {
            "position": position,
        }

        if character is not None:
            entry["slot"] = character["slot"]
            entry["name"] = character["name"]
            entry["class"] = character["class"]

        party.append(entry)

    return party

def decode_character_creation(data, ui_signature):
    effective_stats = list(
        data[
            STATS_EFFECTIVE_ADDR:
            STATS_EFFECTIVE_ADDR + 7
        ]
    )

    base_stats = list(
        data[
            STATS_BASE_ADDR:
            STATS_BASE_ADDR + 7
        ]
    )

    class_id = data[CLASS_ADDR]
    race_id = data[RACE_ADDR]
    alignment_id = data[ALIGNMENT_ADDR]
    sex_id = data[SEX_ADDR]

    name = read_ascii_field(
        data,
        NAME_ADDR,
        NAME_LENGTH,
    )

    if ui_signature == UI_CHARACTER_CLASS:
        class_flags = list(
            data[
                CLASS_FLAGS_ADDR:
                CLASS_FLAGS_ADDR + 6
            ]
        )

        available_classes = [
            CLASS_NAMES[i + 1]
            for i, flag in enumerate(class_flags)
            if flag == CLASS_AVAILABLE_MARKER
        ]

        return {
            "mode": "character_class_selection",
            "rolled_stats": dict(
                zip(STAT_NAMES, base_stats)
            ),
            "available_classes": available_classes,
            "available_actions": {
                "reroll": True,
                "select_class": available_classes,
                "go_back": True,
            },
        }

    if ui_signature == UI_CHARACTER_RACE:
        return {
            "mode": "character_race_selection",
            "stats": dict(
                zip(STAT_NAMES, effective_stats)
            ),
            "selected_class": CLASS_NAMES.get(
                class_id,
                f"unknown_{class_id}",
            ),
            "available_races": [
                "human",
                "elf",
                "dwarf",
                "gnome",
                "half_orc",
            ],
            "available_actions": {
                "select_race": [
                    "human",
                    "elf",
                    "dwarf",
                    "gnome",
                    "half_orc",
                ],
                "start_over": True,
            },
        }

    if ui_signature == UI_CHARACTER_ALIGNMENT:
        return {
            "mode": "character_alignment_selection",
            "stats": dict(
                zip(STAT_NAMES, effective_stats)
            ),
            "selected_class": CLASS_NAMES.get(
                class_id,
                f"unknown_{class_id}",
            ),
            "selected_race": RACE_NAMES.get(
                race_id,
                f"unknown_{race_id}",
            ),
            "available_alignments": [
                "good",
                "neutral",
                "evil",
            ],
            "available_actions": {
                "select_alignment": [
                    "good",
                    "neutral",
                    "evil",
                ],
                "start_over": True,
            },
        }

    if ui_signature == UI_CHARACTER_SEX:
        return {
            "mode": "character_sex_selection",
            "stats": dict(
                zip(STAT_NAMES, effective_stats)
            ),
            "selected_class": CLASS_NAMES.get(
                class_id,
                f"unknown_{class_id}",
            ),
            "selected_race": RACE_NAMES.get(
                race_id,
                f"unknown_{race_id}",
            ),
            "selected_alignment": ALIGNMENT_NAMES.get(
                alignment_id,
                f"unknown_{alignment_id}",
            ),
            "available_sexes": [
                "male",
                "female",
            ],
            "available_actions": {
                "select_sex": [
                    "male",
                    "female",
                ],
                "start_over": True,
            },
        }

    if ui_signature == UI_CHARACTER_NAME:
        return {
            "mode": "character_name_entry",
            "stats": dict(
                zip(STAT_NAMES, effective_stats)
            ),
            "selected_class": CLASS_NAMES.get(
                class_id,
                f"unknown_{class_id}",
            ),
            "selected_race": RACE_NAMES.get(
                race_id,
                f"unknown_{race_id}",
            ),
            "selected_alignment": ALIGNMENT_NAMES.get(
                alignment_id,
                f"unknown_{alignment_id}",
            ),
            "selected_sex": SEX_NAMES.get(
                sex_id,
                f"unknown_{sex_id}",
            ),
            "available_actions": {
                "enter_name": True,
                "start_over": True,
            },
        }
    if ui_signature == UI_CHARACTER_SAVE_CONFIRMATION:
        # Before ENTER is pressed this same creation data contains the
        # completed character. The visible confirmation screen shows it.
        return {
            "mode": "character_save_confirmation",
            "character": {
                "name": name,
                "stats": dict(
                    zip(STAT_NAMES, effective_stats)
                ),
                "class": CLASS_NAMES.get(
                    class_id,
                    f"unknown_{class_id}",
                ),
                "race": RACE_NAMES.get(
                    race_id,
                    f"unknown_{race_id}",
                ),
                "alignment": ALIGNMENT_NAMES.get(
                    alignment_id,
                    f"unknown_{alignment_id}",
                ),
                "sex": SEX_NAMES.get(
                    sex_id,
                    f"unknown_{sex_id}",
                ),
            },
            "available_actions": {
                "confirm_save": True,
                "decline_save": True,
            },
        }

    return {
        "mode": "unknown",
        "available_actions": [],
    }


def is_character_sheet_open(data):
    return (
        data[CHARACTER_SHEET_FLAG_ADDR]
        == CHARACTER_SHEET_FLAG_OPEN
        and
        data[CHARACTER_SHEET_AUX_ADDR]
        == CHARACTER_SHEET_AUX_OPEN
    )


def is_exploration_view_active(ui_signature):
    return ui_signature in EXPLORATION_VIEW_WAIT_IPS

def parse_state(path: Path, include_debug=False, active_wait_return_ip=None):
    data = path.read_bytes()

    if active_wait_return_ip is not None:
        ui_signature = active_wait_return_ip
    else:
        # Offline dump compatibility only.
        ui_signature = read_u16_le(
            data,
            UI_SIGNATURE_ADDR,
        )

    combat_mode = classify_combat_state(data)

    if combat_mode is not None:
        # Full runtime records stay inside the engineering layer.
        # Only information appropriate to the current player-facing
        # state is normalized below.
        party = decode_runtime_party(data)
        combat = inspect_combat_primitives(data)

        state = {
            "mode": combat_mode,
            "available_actions": build_combat_available_actions(
                combat_mode,
                data,
                party,
            ),
        }

        # The normal combat command screen explicitly displays the
        # character whose turn it is ("OPTIONS FOR: <name>").
        if (
            combat_mode == "combat_command"
            and combat["in_combat_turn"]
        ):
            active_position = combat["active_index"] + 1

            active_character = next(
                (
                    character
                    for character in party
                    if character["position"] == active_position
                ),
                None,
            )

            if active_character is not None:
                state["active_character"] = {
                    "position": active_character["position"],
                    "name": active_character["name"],
                }

    elif ui_signature == UI_MAIN_MENU:
        state = {
            "mode": "main_menu",
            "available_actions": {
                "create_character": True,
                "view_characters": True,
                "enter_town": [1, 2, 3, 4, 5],
            },
        }

    elif ui_signature == UI_CHARACTER_ROSTER:
        characters = decode_roster(data)

        state = {
            "mode": "character_roster",
            "characters": characters,
            "available_actions": {
                "view_character": [
                    c["slot"]
                    for c in characters
                ],
                "go_back": True,
            },
        }

    elif ui_signature == UI_EXPLORATION:
        party = decode_runtime_party(data)

        if is_character_sheet_open(data):
            state = {
                "mode": "character_sheet",
                "party": party,
                "available_actions": {
                    "go_back": True,
                },
            }
        else:
            state = {
                "mode": "exploration",
                "party": party,
                "available_actions": {
                    "view_party_character": [
                        character["position"]
                        for character in party
                    ],
                    "forward": True,
                    "back": True,
                    "turn_left": True,
                    "turn_right": True,
                    "search": True,
                },
            }
    elif ui_signature == UI_INN_SORPIGAL:
        (
            characters,
            roster_by_physical_index,
        ) = decode_roster_with_mapping(data)

        party = decode_party(
            data,
            roster_by_physical_index,
        )

        party_slots = {
            member["slot"]
            for member in party
        }

        available_to_add = [
            c["slot"]
            for c in characters
            if c["slot"] not in party_slots
        ]

        removable = [
            member["slot"]
            for member in party
        ]

        state = {
            "mode": "inn",
            "town": "sorpigal",
            "available_characters": characters,
            "party": party,
            "available_actions": {
                "view_character": [
                    c["slot"]
                    for c in characters
                ],
                "add_to_party": available_to_add,
                "remove_from_party": removable,
                "leave_inn": True,
                "go_back": True,
            },
        }
    elif ui_signature in {
        UI_CHARACTER_CLASS,
        UI_CHARACTER_RACE,
        UI_CHARACTER_ALIGNMENT,
        UI_CHARACTER_SEX,
        UI_CHARACTER_NAME,
        UI_CHARACTER_SAVE_CONFIRMATION,
    }:
        state = decode_character_creation(
            data,
            ui_signature,
        )

    else:
        state = {
            "mode": "unknown",
            "available_actions": [],
        }

    # This is an engineering capability flag, deliberately independent of
    # the broader UI-mode classifier. For example, Search result wait 4A1C
    # is not yet a normalized mode but preserves the visible adventure view.
    state["exploration_view_active"] = (
        is_exploration_view_active(ui_signature)
    )

    if include_debug:
        state["_debug"] = {
            "ui_signature_address":
                f"0x{UI_SIGNATURE_ADDR:05X}",
            "ui_signature":
                f"0x{ui_signature:04X}",
        }

    return state


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit(
            "Usage: state.py dump.bin [--debug]"
        )

    include_debug = (
        len(sys.argv) == 3
        and sys.argv[2] == "--debug"
    )

    state = parse_state(
        Path(sys.argv[1]),
        include_debug=include_debug,
    )

    print(
        json.dumps(
            state,
            indent=2,
        )
    )
