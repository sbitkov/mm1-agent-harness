import json
import os
import sys
import time
import uuid
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="replace",
    )


IPC_DIR = Path(__file__).parent / "ipc"
# Must exceed the broker's MM1 boundary timeout plus two engineering
# snapshots. This is IPC transport timeout only, not gameplay settling.
TIMEOUT_SECONDS = 20.0


def emit(payload):
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
    )


def fail(message):
    emit({"error": message})
    raise SystemExit(1)


def transact(payload):
    IPC_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    request_id = uuid.uuid4().hex

    payload = dict(payload)
    payload["id"] = request_id

    request_path = (
        IPC_DIR / f"request_{request_id}.json"
    )

    temp_path = (
        IPC_DIR / f"request_{request_id}.tmp"
    )

    response_path = (
        IPC_DIR / f"response_{request_id}.json"
    )

    temp_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    os.replace(
        temp_path,
        request_path,
    )

    deadline = time.monotonic() + TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        if response_path.exists():
            try:
                response = json.loads(
                    response_path.read_text(
                        encoding="utf-8"
                    )
                )
            finally:
                try:
                    response_path.unlink()
                except OSError:
                    pass

            if not response.get("ok"):
                fail(
                    response.get(
                        "error",
                        "game interface error",
                    )
                )

            return response["result"]

        time.sleep(0.05)

    fail("game interface timeout")


def command_observe():
    return transact({
        "command": "observe",
    })


def command_action(action):
    return transact({
        "command": "action",
        "action": action,
    })


def main():
    if len(sys.argv) < 2:
        fail(
            "commands: observe | press <KEY> | "
            "chord <MODIFIER> <KEY> | type <TEXT>"
        )

    command = sys.argv[1].lower()
    args = sys.argv[2:]

    if command == "observe":
        if args:
            fail("usage: game_cli.py observe")

        result = command_observe()

    elif command == "press":
        if len(args) != 1:
            fail("usage: game_cli.py press <KEY>")

        result = command_action({
            "type": "press",
            "key": args[0],
        })

    elif command == "chord":
        if len(args) != 2:
            fail(
                "usage: game_cli.py "
                "chord <MODIFIER> <KEY>"
            )

        result = command_action({
            "type": "chord",
            "modifier": args[0],
            "key": args[1],
        })

    elif command == "type":
        if not args:
            fail(
                'usage: game_cli.py type "<TEXT>"'
            )

        result = command_action({
            "type": "type_text",
            "text": " ".join(args),
        })

    else:
        fail("unknown command")

    emit(result)


if __name__ == "__main__":
    main()
