from dataclasses import dataclass
import json
from pathlib import Path

from transport import dump_memory
from state import parse_state


ACTIVE_WAIT_PATH = Path(
    r"P:\Astra-MM1\control\active_wait.json"
)


@dataclass(frozen=True)
class EngineeringSnapshot:
    state: dict
    memory: bytes
    active_wait: dict | None


def read_active_wait():
    try:
        payload = json.loads(
            ACTIVE_WAIT_PATH.read_text(encoding="utf-8")
        )

        value = payload.get("return_ip")
        wait_seq = payload.get("wait_seq")

        if not isinstance(value, str):
            return None

        if wait_seq is not None and (
            not isinstance(wait_seq, int)
            or isinstance(wait_seq, bool)
            or wait_seq < 0
        ):
            return None

        return {
            "return_ip": int(value, 16),
            "wait_seq": wait_seq,
        }

    except (
        OSError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ):
        return None


def capture_snapshot(max_attempts=3):
    dump = None
    active_wait = None

    for _ in range(max_attempts):
        before_wait = read_active_wait()
        dump = dump_memory("current.bin")
        active_wait = read_active_wait()

        before_seq = (
            before_wait.get("wait_seq")
            if before_wait is not None
            else None
        )
        after_seq = (
            active_wait.get("wait_seq")
            if active_wait is not None
            else None
        )

        if before_seq == after_seq:
            break
    else:
        raise RuntimeError(
            "MM1 input boundary changed while capturing state"
        )

    assert dump is not None

    return_ip = (
        active_wait["return_ip"]
        if active_wait is not None
        else None
    )

    state = parse_state(
        dump,
        include_debug=False,
        active_wait_return_ip=return_ip,
    )

    return EngineeringSnapshot(
        state=state,
        memory=dump.read_bytes(),
        active_wait=active_wait,
    )


def get_state():
    return capture_snapshot().state


if __name__ == "__main__":
    print(json.dumps(get_state(), indent=2))
