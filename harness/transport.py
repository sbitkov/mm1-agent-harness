from pathlib import Path
import os
import time

CONTROL_DIR = Path(r"P:\Astra-MM1\control")
DEBUG_DIR = Path(r"P:\Astra-MM1\debug")

COMMAND_FILE = CONTROL_DIR / "command.txt"
COMMAND_TMP = CONTROL_DIR / "command.tmp"


def send_command(command: str):
    CONTROL_DIR.mkdir(parents=True, exist_ok=True)

    COMMAND_TMP.write_text(
        command + "\n",
        encoding="ascii",
    )

    os.replace(COMMAND_TMP, COMMAND_FILE)


def press(key: str, timeout=2.0):
    send_command(f"PRESS {key}")

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if not COMMAND_FILE.exists():
            return
        time.sleep(0.01)

    raise TimeoutError(
        f"DOSBox-X did not consume PRESS {key}"
    )


def chord(modifier: str, key: str, timeout=2.0):
    modifier = modifier.upper()
    key = key.upper()

    send_command(f"CHORD {modifier} {key}")

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if not COMMAND_FILE.exists():
            return
        time.sleep(0.01)

    raise TimeoutError(
        f"DOSBox-X did not consume CHORD {modifier} {key}"
    )

def type_text(text: str, key_delay=0.05):
    for ch in text:
        if ch.isalpha():
            press(ch.upper())
        elif ch.isdigit():
            press(ch)
        elif ch == " ":
            press("SPACE")
        else:
            raise ValueError(
                f"Unsupported character for text input: {ch!r}"
            )

        time.sleep(key_delay)


def dump_memory(filename="current.bin", timeout=2.0):
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    output = DEBUG_DIR / filename

    if output.exists():
        output.unlink()

    send_command(f"DUMP {filename}")

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if output.exists() and not COMMAND_FILE.exists():
            return output

        time.sleep(0.01)

    raise TimeoutError(
        f"DOSBox-X did not produce {output}"
    )
