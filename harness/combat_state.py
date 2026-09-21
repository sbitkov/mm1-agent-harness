from __future__ import annotations


# Physical addresses in the 1 MiB DOSBox RAM dump.
PARTY_COUNT_ADDR = 0x1C5B0
ROUND_ADDR = 0x1C5CB

ACTIVE_PTR_ADDR = 0x1C5C6
ACTIVE_INDEX_ADDR = 0x1C5E4

PARTY_PTRS_ADDR = 0x1C698

GROUP_COUNT_ADDR = 0x1C60D

WAIT_INNER_IP_ADDR = 0x289A6
WAIT_RETURN_IP_ADDR = 0x289A8
WAIT_RETURN_CS_ADDR = 0x289AA

# Common blocking keyboard reader.
KEYBOARD_WAIT_INNER_IP = 0x4589
KEYBOARD_WAIT_CS = 0x0D34

# Runtime-confirmed stable input waits.
WAIT_ENCOUNTER_CHOICE = 0x32E9
WAIT_COMBAT_COMMAND = 0x980C
WAIT_COMBAT_EXCHANGE_TARGET = 0x9974
WAIT_COMBAT_SHOOT_TARGET = 0xA35A
WAIT_COMBAT_QUICKREF = 0xC19E

# Static candidates.  These are deliberately NOT enabled as classifiers
# until a stable runtime dump confirms them.
WAIT_COMBAT_DELAY_INPUT_CANDIDATE = 0xB6B7
WAIT_COMBAT_FIGHT_TARGET_CANDIDATE = 0xA2E2
WAIT_COMBAT_USE_ITEM_CANDIDATE = 0xC651


def read_u16(data: bytes, address: int) -> int:
    return data[address] | (data[address + 1] << 8)


def _party_ptrs(data: bytes, count: int) -> list[int]:
    return [
        read_u16(data, PARTY_PTRS_ADDR + 2 * i)
        for i in range(count)
    ]


def inspect_combat_primitives(data: bytes) -> dict:
    """
    Engineering/debug representation.

    These fields are useful for classification but must not be exposed
    wholesale to Astra-player.
    """
    party_count = data[PARTY_COUNT_ADDR]
    active_index = data[ACTIVE_INDEX_ADDR]
    active_ptr = read_u16(data, ACTIVE_PTR_ADDR)
    party_ptrs = _party_ptrs(data, party_count)

    active_character_valid = (
        active_index < party_count
        and active_index < len(party_ptrs)
        and active_ptr == party_ptrs[active_index]
    )

    group_count = data[GROUP_COUNT_ADDR]
    round_number = data[ROUND_ADDR]

    wait_inner_ip = read_u16(data, WAIT_INNER_IP_ADDR)
    wait_return_ip = read_u16(data, WAIT_RETURN_IP_ADDR)
    wait_return_cs = read_u16(data, WAIT_RETURN_CS_ADDR)

    known_input_wait = (
        wait_inner_ip == KEYBOARD_WAIT_INNER_IP
        and wait_return_cs == KEYBOARD_WAIT_CS
    )

    in_combat_context = (
        group_count > 0
        and round_number > 0
    )

    in_combat_turn = (
        in_combat_context
        and active_character_valid
    )

    return {
        "party_count": party_count,
        "active_index": active_index,
        "active_ptr": active_ptr,
        "active_character_valid": active_character_valid,
        "group_count": group_count,
        "round": round_number,
        "wait_inner_ip": wait_inner_ip,
        "wait_return_ip": wait_return_ip,
        "wait_return_cs": wait_return_cs,
        "known_input_wait": known_input_wait,
        "in_combat_context": in_combat_context,
        "in_combat_turn": in_combat_turn,
    }


def classify_combat_state(data: bytes) -> str | None:
    """
    Return a runtime-confirmed combat/encounter state.

    Unknown combat contexts are deliberately classified conservatively.
    None means that these combat predicates do not claim the frame.
    """
    p = inspect_combat_primitives(data)

    if (
        p["known_input_wait"]
        and p["wait_return_ip"] == WAIT_ENCOUNTER_CHOICE
        and p["group_count"] > 0
        and p["round"] == 0
    ):
        return "encounter_choice"

    if (
        p["known_input_wait"]
        and p["in_combat_turn"]
        and p["wait_return_ip"] == WAIT_COMBAT_EXCHANGE_TARGET
    ):
        return "combat_exchange_target"

    if (
        p["known_input_wait"]
        and p["in_combat_turn"]
        and p["wait_return_ip"] == WAIT_COMBAT_SHOOT_TARGET
    ):
        return "combat_shoot_target"

    if (
        p["known_input_wait"]
        and p["in_combat_context"]
        and p["wait_return_ip"] == WAIT_COMBAT_QUICKREF
    ):
        return "combat_quickref"

    if (
        p["known_input_wait"]
        and p["in_combat_turn"]
        and p["wait_return_ip"] == WAIT_COMBAT_COMMAND
    ):
        return "combat_command"

    # Safe fallback: combat is happening, but we have not proved that
    # the game is waiting for one of our supported semantic inputs.
    if p["group_count"] > 0:
        return "combat_transient_or_unknown"

    return None


def debug_summary(data: bytes) -> dict:
    p = inspect_combat_primitives(data)
    return {
        "state": classify_combat_state(data),
        "party_count": p["party_count"],
        "round": p["round"],
        "group_count": p["group_count"],
        "active_index": p["active_index"],
        "active_character_valid": p["active_character_valid"],
        "known_input_wait": p["known_input_wait"],
        "wait_inner_ip": f"0x{p['wait_inner_ip']:04X}",
        "wait_return_ip": f"0x{p['wait_return_ip']:04X}",
        "wait_return_cs": f"0x{p['wait_return_cs']:04X}",
    }