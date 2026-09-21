import json
import time
import traceback
from pathlib import Path

from harness import observe, step_agent


IPC_DIR = Path(r"P:\Astra-MM1\player\ipc")
BROKER_LOG = Path(r"P:\Astra-MM1\logs\broker.log")
ACTION_BOUNDARY_TIMEOUT = 12.0

IPC_DIR.mkdir(parents=True, exist_ok=True)


def log(message):
    BROKER_LOG.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with BROKER_LOG.open(
        "a",
        encoding="utf-8",
    ) as f:
        f.write(message + "\n")


def write_response(request_id, payload):
    target = IPC_DIR / f"response_{request_id}.json"
    temp = IPC_DIR / f"response_{request_id}.tmp"

    temp.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    temp.replace(target)


def validate_action(action):
    if not isinstance(action, dict):
        raise ValueError("invalid action")

    action_type = action.get("type")

    if action_type == "press":
        if (
            not isinstance(action.get("key"), str)
            or not action["key"]
        ):
            raise ValueError("invalid press")

        return

    if action_type == "chord":
        if (
            not isinstance(action.get("modifier"), str)
            or not action["modifier"]
            or not isinstance(action.get("key"), str)
            or not action["key"]
        ):
            raise ValueError("invalid chord")

        return

    if action_type == "type_text":
        if not isinstance(action.get("text"), str):
            raise ValueError("invalid type_text")

        return

    raise ValueError("unsupported action type")


def process_request(path):
    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    request_id = payload.get("id")

    if not isinstance(request_id, str):
        raise ValueError("missing request id")

    command = payload.get("command")

    if command == "observe":
        result = observe()

    elif command == "action":
        action = payload.get("action")
        validate_action(action)

        result = step_agent(
            {"action": action},
            boundary_timeout=ACTION_BOUNDARY_TIMEOUT,
        )

    else:
        raise ValueError("unsupported command")

    write_response(
        request_id,
        {
            "id": request_id,
            "ok": True,
            "result": result,
        },
    )


def main():
    print("MM1 broker running.")
    print(f"IPC: {IPC_DIR}")

    log("broker started")

    while True:
        requests = sorted(
            IPC_DIR.glob("request_*.json")
        )

        for request_path in requests:
            request_id = request_path.stem.removeprefix(
                "request_"
            )

            try:
                process_request(request_path)

            except Exception:
                log(
                    "REQUEST ERROR\n"
                    + traceback.format_exc()
                )

                write_response(
                    request_id,
                    {
                        "id": request_id,
                        "ok": False,
                        "error": "game interface error",
                    },
                )

            finally:
                try:
                    request_path.unlink()
                except OSError:
                    pass

        time.sleep(0.05)


if __name__ == "__main__":
    main()
