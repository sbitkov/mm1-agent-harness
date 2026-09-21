import json
from pathlib import Path


DEFAULT_EVENT_FILE = Path(
    r"P:\Astra-MM1\control\events.ndjson"
)


class EventStream:
    def __init__(self, path=DEFAULT_EVENT_FILE):
        self.path = Path(path)
        self.offset = 0

    def reset(self):
        self.offset = 0

    def read_new(self):
        if not self.path.exists():
            self.offset = 0
            return []

        size = self.path.stat().st_size

        # DOSBox-X restarted and truncated the stream.
        if size < self.offset:
            self.offset = 0

        events = []

        with self.path.open(
            "r",
            encoding="utf-8",
        ) as f:
            f.seek(self.offset)

            while True:
                line = f.readline()

                if not line:
                    break

                line = line.strip()

                if not line:
                    continue

                events.append(
                    json.loads(line)
                )

            self.offset = f.tell()

        return events
