"""
MM1 executable input grammar.

Engineering-layer only.

This module reconstructs the input rules used by Might and Magic Book One
at already-confirmed stable keyboard waits.

It deliberately does NOT produce Astra-facing semantic available_actions.
That translation belongs in a separate normalization layer.

Source of truth:
    actual MM1 input-validation code + runtime predicates/bounds.

Important:
    wait_return_ip must already have been selected by the state classifier.
    There is no universal absolute stack address for all UI depths.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Runtime addresses
# ---------------------------------------------------------------------------

# DS:3BBB
DISPLAY_UPPER_BOUND_ADDR = 0x1C5AB

# DS:3BBC
ROSTER_FILTER_ADDR = 0x1C5AC

# DS:45E8[18]
ROSTER_META_BASE = 0x1CFD8
ROSTER_CAPACITY = 18

# DS:2395[6]
PARTY_SELECTION_ADDR = 0x1AD85
PARTY_SELECTION_SIZE = 6
PARTY_EMPTY = 0xFF

# DS:23BD..23C2
CLASS_ELIGIBILITY_BASE = 0x1ADAD
CLASS_COUNT = 6

# DS:3BC0
PARTY_COUNT_ADDR = 0x1C5B0

# DS:38B4..38B7
COMBAT_F_MARKER_ADDR = 0x1C2A4
COMBAT_S_MARKER_ADDR = 0x1C2A5
COMBAT_C_MARKER_ADDR = 0x1C2A6
COMBAT_A_MARKER_ADDR = 0x1C2A7

# DS:319A
ENEMY_GROUP_UPPER_ADDR = 0x1BB8A

# Character creation name buffer / length.
NAME_LENGTH_ADDR = 0x1C5AB
NAME_BUFFER_ADDR = 0x1AD9D
NAME_MAX_LENGTH = 15


# ---------------------------------------------------------------------------
# Confirmed stable wait return IPs
# ---------------------------------------------------------------------------

WAIT_MAIN_MENU = 0x520B
WAIT_CLASS = 0x531B
WAIT_RACE = 0x546E
WAIT_ALIGNMENT = 0x559D
WAIT_SEX = 0x5660
WAIT_NAME = 0x5737
WAIT_SAVE_CONFIRM = 0x57AC

WAIT_ROSTER = 0x5E79
WAIT_INN = 0x6276
WAIT_EXPLORATION = 0x4CDC

WAIT_ENCOUNTER = 0x32E9
WAIT_COMBAT_COMMAND = 0x980C
WAIT_COMBAT_EXCHANGE = 0x9974
WAIT_COMBAT_SHOOT_TARGET = 0xA35A
WAIT_COMBAT_QUICKREF = 0xC19E


# ---------------------------------------------------------------------------
# Static-only known waits.
#
# Validation code is understood, but these have NOT yet been runtime-confirmed
# as stable dump classifiers. They are therefore intentionally NOT dispatched
# by inspect_input_context().
# ---------------------------------------------------------------------------

STATIC_ONLY_WAITS = {
    0xA2E2: "fight_target",
    0xB6B7: "delay",
    0xC651: "use_item",
}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _byte(data: bytes, addr: int) -> int:
    return data[addr]


def _ascii(value: int) -> str:
    return chr(value)


def _literal(
    key: str,
    effect: str,
    *,
    code: int | None = None,
) -> dict[str, Any]:
    if code is None:
        if len(key) != 1:
            raise ValueError(f"literal key needs explicit code: {key!r}")
        code = ord(key)

    return {
        "kind": "literal",
        "key": key,
        "code": code,
        "effect": effect,
        "enabled": True,
    }


def _modified(
    key: str,
    effect: str,
    *,
    code: int,
) -> dict[str, Any]:
    return {
        "kind": "literal_modified",
        "key": key,
        "code": code,
        "effect": effect,
        "enabled": True,
    }


def _range(
    low: int,
    high: int,
    effect: str,
    *,
    inclusive_high: bool = True,
    source: str | None = None,
) -> dict[str, Any]:
    return {
        "kind": "dynamic_range",
        "low": low,
        "high": high,
        "low_key": _ascii(low),
        "high_key": _ascii(high) if high >= low else None,
        "inclusive_high": inclusive_high,
        "effect": effect,
        "source": source,
        "enabled": high >= low,
    }


def _conditional(
    key: str,
    effect: str,
    enabled: bool,
    *,
    predicate: str,
    code: int | None = None,
) -> dict[str, Any]:
    if code is None:
        code = ord(key)

    return {
        "kind": "conditional",
        "key": key,
        "code": code,
        "effect": effect,
        "enabled": bool(enabled),
        "predicate": predicate,
    }


def _marker(
    data: bytes,
    key: str,
    effect: str,
    addr: int,
) -> dict[str, Any]:
    value = _byte(data, addr)

    return {
        "kind": "runtime_marker",
        "key": key,
        "code": ord(key),
        "effect": effect,
        "enabled": value != 0x20,
        "addr": addr,
        "value": value,
        "predicate": "!= 0x20",
    }


def _get_wait_return_ip(classified_state: Any) -> int:
    """
    Accept either:

        {"wait_return_ip": 0x....}

    or an object with:

        classified_state.wait_return_ip
    """

    if isinstance(classified_state, dict):
        value = classified_state.get("wait_return_ip")
    else:
        value = getattr(classified_state, "wait_return_ip", None)

    if value is None:
        raise ValueError(
            "classified_state does not contain wait_return_ip"
        )

    return int(value)


def _party_count(data: bytes) -> int:
    return min(6, _byte(data, PARTY_COUNT_ADDR))


def _party_selection(data: bytes) -> list[int]:
    return list(
        data[
            PARTY_SELECTION_ADDR:
            PARTY_SELECTION_ADDR + PARTY_SELECTION_SIZE
        ]
    )


def _roster_has_free_physical_slot(data: bytes) -> bool:
    return any(
        _byte(data, ROSTER_META_BASE + i) == 0
        for i in range(ROSTER_CAPACITY)
    )


def _class_is_eligible(data: bytes, class_digit: int) -> bool:
    if not 1 <= class_digit <= CLASS_COUNT:
        return False

    return (
        _byte(
            data,
            CLASS_ELIGIBILITY_BASE + class_digit - 1,
        )
        != 0
    )


def _display_letters(data: bytes) -> tuple[int, int]:
    """
    At roster / Inn stable waits, DS:3BBB contains the exclusive
    upper bound used directly by the game's validation code.

    Example:
        A..L visible
        bound == ord('M')
    """

    low = ord("A")
    high_exclusive = _byte(data, DISPLAY_UPPER_BOUND_ADDR)
    return low, high_exclusive


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------

def _main_menu(data: bytes) -> dict[str, Any]:
    return {
        "context": "main_menu",
        "rules": [
            _literal("C", "create_character"),
            _literal("V", "view_characters"),
            _range(
                ord("1"),
                ord("5"),
                "enter_town",
                source="static_validation",
            ),
        ],
        "rejected_input": "loop_same_reader",
    }


def _class_selection(data: bytes) -> dict[str, Any]:
    free_slot = _roster_has_free_physical_slot(data)

    rules: list[dict[str, Any]] = [
        _literal(
            "ESC",
            "abandon_creation",
            code=0x1B,
        ),
        _literal(
            "ENTER",
            "reroll_stats",
            code=0x0D,
        ),
    ]

    for digit in range(1, 7):
        rules.append(
            _conditional(
                str(digit),
                "select_class",
                free_slot and _class_is_eligible(data, digit),
                predicate=(
                    "roster_has_free_physical_slot "
                    "and class_eligibility_flag != 0"
                ),
            )
        )

    return {
        "context": "class_selection",
        "rules": rules,
        "runtime": {
            "roster_has_free_physical_slot": free_slot,
            "class_eligibility": {
                str(digit): _class_is_eligible(data, digit)
                for digit in range(1, 7)
            },
        },
        "rejected_input": "loop_same_reader",
    }


def _race_selection(data: bytes) -> dict[str, Any]:
    return {
        "context": "race_selection",
        "rules": [
            _literal(
                "ESC",
                "abandon_creation",
                code=0x1B,
            ),
            _range(
                ord("1"),
                ord("5"),
                "select_race",
                source="static_validation",
            ),
        ],
        "rejected_input": "loop_same_reader",
    }


def _alignment_selection(data: bytes) -> dict[str, Any]:
    return {
        "context": "alignment_selection",
        "rules": [
            _literal(
                "ESC",
                "abandon_creation",
                code=0x1B,
            ),
            _range(
                ord("1"),
                ord("3"),
                "select_alignment",
                source="static_validation",
            ),
        ],
        "rejected_input": "loop_same_reader",
    }


def _sex_selection(data: bytes) -> dict[str, Any]:
    return {
        "context": "sex_selection",
        "rules": [
            _literal(
                "ESC",
                "abandon_creation",
                code=0x1B,
            ),
            _range(
                ord("1"),
                ord("2"),
                "select_sex",
                source="static_validation",
            ),
        ],
        "rejected_input": "loop_same_reader",
    }


def _name_entry(data: bytes) -> dict[str, Any]:
    length = _byte(data, NAME_LENGTH_ADDR)

    rules: list[dict[str, Any]] = [
        _literal(
            "BACKSPACE",
            "clear_name",
            code=0x08,
        ),
        _literal(
            "ESC",
            "abandon_creation",
            code=0x1B,
        ),
        _conditional(
            "ENTER",
            "finish_name",
            length != 0,
            predicate="name_length != 0",
            code=0x0D,
        ),
    ]

    # The game accepts normalized 0x20..0x7A inclusive.
    #
    # At length 15 there is no further stable name-input wait:
    # the accepted 15th printable character falls through to completion.
    rules.append(
        {
            "kind": "printable_range",
            "low": 0x20,
            "high": 0x7A,
            "inclusive_high": True,
            "effect": "append_name_character",
            "enabled": length < NAME_MAX_LENGTH,
            "current_length": length,
            "max_length": NAME_MAX_LENGTH,
            "completion_on_reaching_max": True,
        }
    )

    return {
        "context": "name_entry",
        "rules": rules,
        "runtime": {
            "name_length": length,
            "max_length": NAME_MAX_LENGTH,
        },
        "rejected_input": "loop_same_reader",
    }


def _save_confirmation(data: bytes) -> dict[str, Any]:
    return {
        "context": "save_confirmation",
        "rules": [
            _literal("Y", "save_character"),
            _literal("N", "discard_character"),
        ],
        "rejected_input": "loop_same_reader",
    }


def _roster(data: bytes) -> dict[str, Any]:
    low, high_exclusive = _display_letters(data)

    rules: list[dict[str, Any]] = [
        _literal(
            "ESC",
            "back_to_main_menu",
            code=0x1B,
        ),
    ]

    if high_exclusive > low:
        rules.append(
            {
                "kind": "dynamic_range",
                "low": low,
                "high_exclusive": high_exclusive,
                "low_key": chr(low),
                "high_key": chr(high_exclusive - 1),
                "effect": "view_character",
                "source_addr": DISPLAY_UPPER_BOUND_ADDR,
                "enabled": True,
            }
        )

    return {
        "context": "character_roster",
        "rules": rules,
        "runtime": {
            "display_upper_exclusive": high_exclusive,
            "display_count": max(0, high_exclusive - low),
        },
        "rejected_input": "loop_same_reader",
    }


def _inn(data: bytes) -> dict[str, Any]:
    low, high_exclusive = _display_letters(data)
    party = _party_selection(data)
    roster_filter = _byte(data, ROSTER_FILTER_ADDR)

    any_selected = any(
        value != PARTY_EMPTY
        for value in party
    )

    has_empty_cell = PARTY_EMPTY in party

    # Reconstruct the same dense displayed-ordinal -> physical-index
    # mapping used by MM1's Inn Ctrl+A..N handler.
    displayed_physical_indices: list[int] = []

    for physical_index in range(ROSTER_CAPACITY):
        if (
            _byte(data, ROSTER_META_BASE + physical_index)
            == roster_filter
        ):
            displayed_physical_indices.append(physical_index)

    rules: list[dict[str, Any]] = [
        _literal(
            "ESC",
            "leave_to_main_menu",
            code=0x1B,
        ),
        _conditional(
            "X",
            "exit_inn",
            any_selected,
            predicate="any party selection cell != 0xFF",
        ),
    ]

    if high_exclusive > low:
        rules.append(
            {
                "kind": "dynamic_range",
                "low": low,
                "high_exclusive": high_exclusive,
                "low_key": chr(low),
                "high_key": chr(high_exclusive - 1),
                "effect": "view_character",
                "source_addr": DISPLAY_UPPER_BOUND_ADDR,
                "enabled": True,
            }
        )

    # Ctrl+A == ordinal 0, Ctrl+B == ordinal 1, ...
    #
    # Resolve each visible ordinal exactly as the game does, then describe
    # the actual executable toggle operation.
    visible_count = min(
        max(0, high_exclusive - low),
        len(displayed_physical_indices),
    )

    for ordinal in range(visible_count):
        physical_index = displayed_physical_indices[ordinal]
        display_letter = chr(ord("A") + ordinal)
        ctrl_code = ordinal + 1

        already_selected = physical_index in party

        if already_selected:
            effect = "remove_from_party"
            enabled = True
            predicate = "physical roster index already selected"
        else:
            effect = "add_to_party"
            enabled = has_empty_cell
            predicate = "party has 0xFF cell"

        rules.append(
            {
                "kind": "conditional_modified",
                "key": f"CTRL+{display_letter}",
                "code": ctrl_code,
                "effect": effect,
                "slot": display_letter,
                "physical_index": physical_index,
                "enabled": enabled,
                "predicate": predicate,
            }
        )

    return {
        "context": "inn",
        "rules": rules,
        "runtime": {
            "display_upper_exclusive": high_exclusive,
            "display_count": max(0, high_exclusive - low),
            "party_selection": party,
            "party_has_member": any_selected,
            "party_has_empty_cell": has_empty_cell,
            "roster_filter": roster_filter,

            # Engineering-only. Never expose these physical indices
            # directly to Astra.
            "displayed_physical_indices": displayed_physical_indices,
        },
        "rejected_input": "loop_same_reader",
    }

def _exploration(data: bytes) -> dict[str, Any]:
    party_count = _byte(data, PARTY_COUNT_ADDR)

    rules: list[dict[str, Any]] = [
        _literal(
            "ENTER",
            "forward",
            code=0x0D,
        ),
        _literal(
            "UP",
            "forward",
            code=0xC8,
        ),
        _literal(
            "DOWN",
            "back",
            code=0xD0,
        ),
        _literal(
            "BACKSPACE",
            "turn_left",
            code=0x08,
        ),
        _literal(
            "LEFT",
            "turn_left",
            code=0xCB,
        ),
        _literal(
            "RIGHT",
            "turn_right",
            code=0xCD,
        ),
        _literal("O", "order_party"),
        _literal("R", "rest"),
        _literal("S", "search"),
        _literal("B", "bash"),
        _literal("U", "unlock"),
        _literal("Q", "quick_reference"),
        _literal("P", "protect"),
        _literal("V", "toggle_volume"),
    ]

    if party_count > 0:
        rules.append(
            _range(
                ord("1"),
                ord("0") + party_count,
                "view_party_character",
                source="party_count",
            )
        )

    return {
        "context": "exploration",
        "rules": rules,
        "runtime": {
            "party_count": party_count,
        },
        "rejected_input": "loop_same_reader",
    }

def _encounter(data: bytes) -> dict[str, Any]:
    return {
        "context": "encounter_choice",
        "rules": [
            _literal("A", "attack"),
            _literal("R", "retreat"),
            _literal("S", "surrender"),
            _literal("B", "bribe"),
        ],
        "rejected_input": "loop_same_reader",
    }


def _combat_command(data: bytes) -> dict[str, Any]:
    count = _party_count(data)

    rules: list[dict[str, Any]] = [
        _modified(
            "CTRL+A",
            "context_shortcut",
            code=0x01,
        ),

        _marker(
            data,
            "A",
            "attack",
            COMBAT_A_MARKER_ADDR,
        ),
        _marker(
            data,
            "F",
            "fight",
            COMBAT_F_MARKER_ADDR,
        ),
        _marker(
            data,
            "S",
            "shoot",
            COMBAT_S_MARKER_ADDR,
        ),

        # C is special in the original validation:
        # both branches handle the key.  Marker presence determines
        # whether this is a real cast path or an unavailable/info path.
        {
            "kind": "runtime_marker",
            "key": "C",
            "code": ord("C"),
            "effect": (
                "cast"
                if _byte(data, COMBAT_C_MARKER_ADDR) != 0x20
                else "cast_unavailable_info"
            ),
            "enabled": True,
            "addr": COMBAT_C_MARKER_ADDR,
            "value": _byte(data, COMBAT_C_MARKER_ADDR),
            "predicate": "both marker states handle C",
        },

        _literal("D", "delay"),
        _literal("P", "protection_view"),
        _literal("Q", "quick_reference"),
        _literal("U", "use_item"),

        _conditional(
            "E",
            "exchange",
            count != 1,
            predicate="party_count != 1",
        ),

        _literal("R", "retreat"),
        _literal("B", "block"),
    ]

    if count > 0:
        rules.append(
            _range(
                ord("1"),
                ord("0") + count,
                "view_party_character",
                source="party_count",
            )
        )

    return {
        "context": "combat_command",
        "rules": rules,
        "runtime": {
            "party_count": count,
            "markers": {
                "F": _byte(data, COMBAT_F_MARKER_ADDR),
                "S": _byte(data, COMBAT_S_MARKER_ADDR),
                "C": _byte(data, COMBAT_C_MARKER_ADDR),
                "A": _byte(data, COMBAT_A_MARKER_ADDR),
            },
        },
        "rejected_input": "loop_same_reader",
    }


def _combat_exchange(data: bytes) -> dict[str, Any]:
    count = _party_count(data)

    rules: list[dict[str, Any]] = [
        _literal(
            "ESC",
            "cancel_exchange",
            code=0x1B,
        ),
    ]

    if count > 0:
        rules.append(
            _range(
                ord("1"),
                ord("0") + count,
                "exchange_with_party_position",
                source="party_count",
            )
        )

    return {
        "context": "combat_exchange_target",
        "rules": rules,
        "runtime": {
            "party_count": count,
        },
        "rejected_input": "loop_same_reader",
    }


def _combat_shoot_target(data: bytes) -> dict[str, Any]:
    upper = _byte(data, ENEMY_GROUP_UPPER_ADDR)

    rules: list[dict[str, Any]] = [
        _literal(
            "ESC",
            "cancel_target_selection",
            code=0x1B,
        ),
    ]

    if upper >= ord("A"):
        rules.append(
            _range(
                ord("A"),
                upper,
                "select_enemy_group",
                source="enemy_group_upper_bound",
            )
        )

    return {
        "context": "combat_shoot_target",
        "rules": rules,
        "runtime": {
            "enemy_group_upper_inclusive": upper,
        },
        "rejected_input": "loop_same_reader",
    }


def _combat_quickref(data: bytes) -> dict[str, Any]:
    count = _party_count(data)

    rules: list[dict[str, Any]] = []

    if count > 0:
        rules.append(
            _range(
                ord("1"),
                ord("0") + count,
                "view_party_character",
                source="party_count",
            )
        )

    rules.append(
        {
            "kind": "catch_all",
            "effect": "dismiss_quick_reference",
            "enabled": True,

            # Important distinction:
            #
            # The executable game behavior is "anything else dismisses".
            # The future semantic Astra-facing layer should expose ESC as
            # the canonical player-visible dismiss action instead of
            # advertising arbitrary garbage keys.
            "player_affordance": False,
            "canonical_key": "ESC",
        }
    )

    return {
        "context": "combat_quick_reference",
        "rules": rules,
        "runtime": {
            "party_count": count,
        },
        "rejected_input": None,
        "fallback_input": "dismiss",
    }


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_BUILDERS = {
    WAIT_MAIN_MENU: _main_menu,
    WAIT_CLASS: _class_selection,
    WAIT_RACE: _race_selection,
    WAIT_ALIGNMENT: _alignment_selection,
    WAIT_SEX: _sex_selection,
    WAIT_NAME: _name_entry,
    WAIT_SAVE_CONFIRM: _save_confirmation,

    WAIT_ROSTER: _roster,
    WAIT_INN: _inn,
    WAIT_EXPLORATION: _exploration,

    WAIT_ENCOUNTER: _encounter,
    WAIT_COMBAT_COMMAND: _combat_command,
    WAIT_COMBAT_EXCHANGE: _combat_exchange,
    WAIT_COMBAT_SHOOT_TARGET: _combat_shoot_target,
    WAIT_COMBAT_QUICKREF: _combat_quickref,
}


def build_rules_for_wait_ip(
    wait_return_ip: int,
    data: bytes,
) -> dict[str, Any]:
    """
    Build executable MM1 input rules for a confirmed stable wait.

    Unknown or static-only waits are deliberately not guessed.
    """

    if wait_return_ip in STATIC_ONLY_WAITS:
        return {
            "wait_return_ip": wait_return_ip,
            "context": STATIC_ONLY_WAITS[wait_return_ip],
            "stable_classifier_enabled": False,
            "rules": [],
            "reason": (
                "input validation is statically understood, "
                "but this wait is not runtime-confirmed as a "
                "stable classifier"
            ),
        }

    builder = _BUILDERS.get(wait_return_ip)

    if builder is None:
        return {
            "wait_return_ip": wait_return_ip,
            "context": "unknown",
            "stable_classifier_enabled": False,
            "rules": [],
            "reason": "unknown confirmed input wait",
        }

    result = builder(data)

    return {
        "wait_return_ip": wait_return_ip,
        "stable_classifier_enabled": True,
        **result,
    }


def inspect_input_context(
    data: bytes,
    classified_state: Any,
) -> dict[str, Any]:
    """
    Public entry point.

    The state classifier remains responsible for deciding which stack
    location / stable wait is authoritative.

    This function only interprets that already-selected wait_return_ip.
    """

    wait_return_ip = _get_wait_return_ip(classified_state)

    return build_rules_for_wait_ip(
        wait_return_ip,
        data,
    )
