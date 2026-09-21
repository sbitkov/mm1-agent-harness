SYSTEM_NOTE_STATUSES = {
    "observation",
    "hypothesis",
    "testing",
    "supported",
    "rejected",
}

BREAK_REPORT_STATUSES = {
    "interesting",
    "strong",
    "suspected_break",
    "confirmed_break",
}


def validate_action(state, action):
    if not isinstance(action, dict):
        raise TypeError("action must be an object")

    action_type = action.get("type")

    if action_type == "press":
        key = action.get("key")

        if not isinstance(key, str) or not key:
            raise ValueError(
                "press requires a non-empty key"
            )

        return

    if action_type == "chord":
        modifier = action.get("modifier")
        key = action.get("key")

        if (
            not isinstance(modifier, str)
            or not modifier
        ):
            raise ValueError(
                "chord requires a modifier"
            )

        if not isinstance(key, str) or not key:
            raise ValueError(
                "chord requires a key"
            )

        return

    if action_type == "type_text":
        text = action.get("text")

        if not isinstance(text, str) or not text:
            raise ValueError(
                "type_text requires non-empty text"
            )

        return

    name = action.get("action")
    available = state.get("available_actions", {})

    # Simple boolean actions.
    if name in (
        "create_character",
        "view_characters",
        "forward",
        "back",
        "turn_left",
        "turn_right",
        "search",
        "toggle_volume",
        "unlock",
        "bash",
        "rest",
        "order_party",
        "reroll",
        "leave_inn",
        "go_back",
        "start_over",
        "confirm_save",
        "decline_save",
        "attack",
        "bribe",
        "surrender",
        "fight",
        "shoot",
        "cast",
        "delay",
        "protect",
        "quick_reference",
        "exchange",
        "retreat",
        "use",
        "block",
    ):
        if not available.get(name):
            raise ValueError(
                f"{name} is not currently available"
            )
        return

    if name == "enter_town":
        town = action.get("town")
        allowed = available.get("enter_town", [])

        if town not in allowed:
            raise ValueError(
                f"town {town!r} is not currently available"
            )
        return

    if name == "view_character":
        slot = action.get("slot")
        allowed = available.get("view_character", [])

        if slot not in allowed:
            raise ValueError(
                f"slot {slot!r} is not currently viewable"
            )
        return

    if name in ("add_to_party", "remove_from_party"):
        slot = action.get("slot")
        allowed = available.get(name, [])

        if slot not in allowed:
            raise ValueError(
                f"slot {slot!r} is not valid for {name}"
            )
        return

    if name == "view_party_character":
        position = action.get("position")
        allowed = available.get(
            "view_party_character",
            [],
        )

        if position not in allowed:
            raise ValueError(
                f"party position {position!r} "
                "is not currently viewable"
            )
        return

    if name == "select_exchange_target":
        position = action.get("position")
        allowed = available.get(
            "select_exchange_target",
            [],
        )

        if position not in allowed:
            raise ValueError(
                f"party position {position!r} "
                "is not a valid exchange target"
            )
        return

    if name == "select_enemy_group":
        group = action.get("group")

        if isinstance(group, str):
            group = group.upper()

        allowed = available.get(
            "select_enemy_group",
            [],
        )

        if group not in allowed:
            raise ValueError(
                f"enemy group {group!r} "
                "is not currently targetable"
            )
        return

    if name == "select_class":
        value = action.get("class")
        allowed = available.get(
            "select_class",
            [],
        )

    elif name == "select_race":
        value = action.get("race")
        allowed = available.get(
            "select_race",
            [],
        )

    elif name == "select_alignment":
        value = action.get("alignment")
        allowed = available.get(
            "select_alignment",
            [],
        )

    elif name == "select_sex":
        value = action.get("sex")
        allowed = available.get(
            "select_sex",
            [],
        )

    elif name == "enter_name":
        if not available.get("enter_name"):
            raise ValueError(
                "enter_name is not currently available"
            )

        value = action.get("name")

        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                "enter_name requires a non-empty name"
            )

        if len(value) > 15:
            raise ValueError(
                "name is too long for "
                "the current conservative limit"
            )

        return

    else:
        raise ValueError(
            f"unknown action: {name!r}"
        )

    if value not in allowed:
        raise ValueError(
            f"{value!r} is not currently "
            f"allowed for {name}"
        )

def validate_agent_response(state, response):
    if not isinstance(response, dict):
        raise TypeError("agent response must be an object")

    if "action" not in response:
        raise ValueError("agent response must contain an action")

    validate_action(state, response["action"])

    journal_entry = response.get("journal_entry")

    if journal_entry is not None:
        if not isinstance(journal_entry, str):
            raise TypeError("journal_entry must be a string")
        if not journal_entry.strip():
            raise ValueError("journal_entry cannot be empty")

    system_note = response.get("system_note")

    if system_note is not None:
        if not isinstance(system_note, dict):
            raise TypeError("system_note must be an object")

        status = system_note.get("status")
        text = system_note.get("text")

        if status not in SYSTEM_NOTE_STATUSES:
            raise ValueError(
                f"invalid system_note status: {status!r}"
            )

        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                "system_note.text must be a non-empty string"
            )

    break_report = response.get("break_report")

    if break_report is not None:
        if not isinstance(break_report, dict):
            raise TypeError("break_report must be an object")

        status = break_report.get("status")
        title = break_report.get("title")

        if status not in BREAK_REPORT_STATUSES:
            raise ValueError(
                f"invalid break_report status: {status!r}"
            )

        if not isinstance(title, str) or not title.strip():
            raise ValueError(
                "break_report.title must be a non-empty string"
            )
