from transport import press, chord, type_text

CLASS_KEYS = {
    "knight": "1",
    "paladin": "2",
    "archer": "3",
    "cleric": "4",
    "sorcerer": "5",
    "robber": "6",
}

RACE_KEYS = {
    "human": "1",
    "elf": "2",
    "dwarf": "3",
    "gnome": "4",
    "half_orc": "5",
}

ALIGNMENT_KEYS = {
    "good": "1",
    "neutral": "2",
    "evil": "3",
}

SEX_KEYS = {
    "male": "1",
    "female": "2",
}


def apply_action(action):
    if not isinstance(action, dict):
        raise TypeError("Action must be a dict")

    action_type = action.get("type")

    if action_type == "press":
        key = action.get("key")

        if not isinstance(key, str) or not key:
            raise ValueError("press requires a non-empty key")

        press(key)
        return

    if action_type == "chord":
        modifier = action.get("modifier")
        key = action.get("key")

        if not isinstance(modifier, str) or not modifier:
            raise ValueError("chord requires modifier")

        if not isinstance(key, str) or not key:
            raise ValueError("chord requires key")

        chord(modifier, key)
        return

    if action_type == "type_text":
        text = action.get("text")

        if not isinstance(text, str) or not text:
            raise ValueError("type_text requires non-empty text")

        type_text(text)
        return

    name = action.get("action")

    if name == "create_character":
        press("C")
        return

    if name == "view_characters":
        press("V")
        return

    if name == "enter_town":
        town = action.get("town")

        if not isinstance(town, int):
            raise TypeError("enter_town requires an integer town")

        if town < 1 or town > 5:
            raise ValueError("town must be between 1 and 5")

        press(str(town))
        return

    if name == "view_character":
        slot = action.get("slot")

        if not isinstance(slot, str) or len(slot) != 1:
            raise ValueError("view_character requires a one-letter slot")

        press(slot.upper())
        return

    if name in ("add_to_party", "remove_from_party"):
        slot = action.get("slot")

        if not isinstance(slot, str) or len(slot) != 1:
            raise ValueError(
                f"{name} requires a one-letter slot"
            )

        chord("CTRL", slot.upper())
        return

    if name == "leave_inn":
        press("X")
        return
    if name == "forward":
        press("UP")
        return

    if name == "back":
        press("DOWN")
        return

    if name == "turn_left":
        press("LEFT")
        return

    if name == "turn_right":
        press("RIGHT")
        return

    if name == "search":
        press("S")
        return

    if name == "order_party":
        press("O")
        return

    if name == "rest":
        press("R")
        return

    if name == "bash":
        press("B")
        return

    if name == "unlock":
        press("U")
        return

    if name == "toggle_volume":
        press("V")
        return
    if name == "reroll":
        press("ENTER")
        return

    if name == "go_back" or name == "start_over":
        press("ESC")
        return

    if name == "view_party_character":
        position = action.get("position")

        if not isinstance(position, int):
            raise ValueError("position must be an integer")

        if not 1 <= position <= 6:
            raise ValueError("position must be between 1 and 6")

        press(str(position))
        return
    if name == "attack":
        press("A")
        return

    if name == "bribe":
        press("B")
        return

    if name == "surrender":
        press("S")
        return

    if name == "fight":
        press("F")
        return

    if name == "shoot":
        press("S")
        return

    if name == "cast":
        press("C")
        return

    if name == "delay":
        press("D")
        return

    if name == "protect":
        press("P")
        return

    if name == "quick_reference":
        press("Q")
        return

    if name == "exchange":
        press("E")
        return

    if name == "retreat":
        press("R")
        return

    if name == "use":
        press("U")
        return

    if name == "block":
        press("B")
        return

    if name == "select_exchange_target":
        position = action.get("position")

        if not isinstance(position, int):
            raise ValueError(
                "select_exchange_target requires integer position"
            )

        if not 1 <= position <= 6:
            raise ValueError(
                "exchange position must be between 1 and 6"
            )

        press(str(position))
        return

    if name == "select_enemy_group":
        group = action.get("group")

        if (
            not isinstance(group, str)
            or len(group) != 1
            or not group.isalpha()
        ):
            raise ValueError(
                "select_enemy_group requires one letter"
            )

        press(group.upper())
        return
    if name == "select_class":
        press(CLASS_KEYS[action["class"]])
        return

    if name == "select_race":
        press(RACE_KEYS[action["race"]])
        return

    if name == "select_alignment":
        press(ALIGNMENT_KEYS[action["alignment"]])
        return

    if name == "select_sex":
        press(SEX_KEYS[action["sex"]])
        return

    if name == "enter_name":
        name_value = action.get("name", "")

        if not isinstance(name_value, str):
            raise TypeError("name must be a string")

        if not name_value:
            raise ValueError("name cannot be empty")

        type_text(name_value)
        press("ENTER")
        return

    if name == "confirm_save":
        press("Y")
        return

    if name == "decline_save":
        press("N")
        return

    raise ValueError(
        f"Unknown action: {name!r}"
    )
