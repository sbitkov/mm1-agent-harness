from pathlib import Path
from datetime import datetime, timezone
import json

from live_state import capture_snapshot
from actions import apply_action
from agent_protocol import validate_agent_response
from available_state import build_observation
from event_stream import EventStream
from wait_boundary import require_wait_seq, wait_for_next_boundary


ROOT = Path(r"P:\Astra-MM1")

LOG_DIR = ROOT / "logs"
NOTES_DIR = ROOT / "notes"

LOG_DIR.mkdir(parents=True, exist_ok=True)
NOTES_DIR.mkdir(parents=True, exist_ok=True)

SESSION_ID = datetime.now().strftime("%Y%m%d-%H%M%S")

SESSION_LOG = LOG_DIR / f"session-{SESSION_ID}.jsonl"

ADVENTURE_LOG = NOTES_DIR / "adventure-journal.jsonl"
SYSTEM_LOG = NOTES_DIR / "system-notes.jsonl"
BREAK_LOG = NOTES_DIR / "break-reports.jsonl"

_step_counter = 0
_event_stream = EventStream()


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path, record):
    with path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                record,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n"
        )


def observe():
    snapshot = capture_snapshot()
    engineering_state = snapshot.state

    observation = build_observation(
        snapshot.memory,
        engineering_state=engineering_state,
    )

    _append_jsonl(
        SESSION_LOG,
        {
            "type": "observation",
            "session": SESSION_ID,
            "timestamp": _utc_now(),

            # Kept for research/debugging only.
            # This object must not be sent to Astra.
            "engineering_state": engineering_state,

            # This is the actual Astra-facing observation.
            "observation": observation,
        },
    )

    return observation


def step_agent(response, boundary_timeout=10.0):
    global _step_counter

    # Internal engineering state.
    # Astra must never receive this object directly.
    before_snapshot = capture_snapshot()
    before = before_snapshot.state
    old_wait_seq = require_wait_seq(
        before_snapshot.active_wait
    )

    validate_agent_response(before, response)

    timestamp = _utc_now()

    journal_entry = response.get("journal_entry")
    system_note = response.get("system_note")
    break_report = response.get("break_report")

    if journal_entry is not None:
        _append_jsonl(
            ADVENTURE_LOG,
            {
                "session": SESSION_ID,
                "timestamp": timestamp,
                "step": _step_counter + 1,
                "entry": journal_entry,
                "state": before,
            },
        )

    if system_note is not None:
        _append_jsonl(
            SYSTEM_LOG,
            {
                "session": SESSION_ID,
                "timestamp": timestamp,
                "step": _step_counter + 1,
                "note": system_note,
                "state": before,
            },
        )

    if break_report is not None:
        _append_jsonl(
            BREAK_LOG,
            {
                "session": SESSION_ID,
                "timestamp": timestamp,
                "step": _step_counter + 1,
                "report": break_report,
                "state": before,
            },
        )

    # Establish the event boundary for this action.
    _event_stream.read_new()

    apply_action(response["action"])

    next_wait = wait_for_next_boundary(
        old_wait_seq,
        timeout=boundary_timeout,
    )

    events = _event_stream.read_new()

    # Internal state after the action.
    after_snapshot = capture_snapshot()
    after = after_snapshot.state

    # Player-visible projection only.
    observation = build_observation(
        after_snapshot.memory,
        events,
        engineering_state=after,
    )

    _step_counter += 1

    _append_jsonl(
        SESSION_LOG,
        {
            "type": "step",
            "session": SESSION_ID,
            "step": _step_counter,
            "timestamp": timestamp,

            # Engineering-only diagnostic record.
            "engineering_state": before,

            "agent_response": response,

            # Raw player-visible event channel.
            "events": events,

            # Engineering-only diagnostic record.
            "next_engineering_state": after,

            "boundary": {
                "previous_wait_seq": old_wait_seq,
                "next_wait_seq": next_wait["wait_seq"],
                "next_return_ip": (
                    f"0x{next_wait['return_ip']:04X}"
                ),
            },

            # Exactly what was returned to Astra.
            "observation": observation,
        },
    )

    return observation


def get_paths():
    return {
        "session_log": SESSION_LOG,
        "adventure_journal": ADVENTURE_LOG,
        "system_notes": SYSTEM_LOG,
        "break_reports": BREAK_LOG,
    }
