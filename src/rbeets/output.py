"""Print events: as JSON lines for programs, as text for people."""

from __future__ import annotations

import json
import sys


def json_handler(event: dict) -> None:
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


def human_handler(event: dict) -> None:
    kind = event["type"]
    if kind == "progress":
        total = "?" if event["total"] is None else event["total"]
        outcome = f" ({event['outcome']})" if "outcome" in event else ""
        if event.get("match"):
            outcome = f" ({event['outcome']}: {event['match']}, distance {event['distance']}, release {event['release']})"
        print(f"{event['done']}/{total} {event['album']}{outcome}", file=sys.stderr)
    elif kind == "log":
        print(f"{event['level']}: {event['message']}", file=sys.stderr)
    elif kind == "error":
        print(f"rbeets: {event['message']}", file=sys.stderr)
    elif kind == "result":
        for key, value in event.items():
            if key in ("type", "command"):
                continue
            if isinstance(value, list):
                print(f"{key}: {len(value)}")
                for entry in value:
                    text = " | ".join(map(str, entry.values())) if isinstance(entry, dict) else str(entry)
                    print(f"  {text}")
            else:
                print(f"{key}: {value}")
