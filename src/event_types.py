"""Shared event categories used by the frontend and Calendar API."""
import json
import re
from pathlib import Path
EVENT_TYPES = json.loads((Path(__file__).resolve().parents[1] / "frontend/src/eventTypes.json").read_text())
def event_type(event):
    kind = event.get("type")
    if kind in EVENT_TYPES:
        return kind
    title = event.get("title", "").lower()
    for word, category in [("exam", "exam"), ("midterm", "exam"), ("final", "exam"), ("quiz", "exam"), ("lab", "lab"), ("recitation", "recitation")]:
        if re.search(r"\b" + word + r"\b", title):
            return category
    return "lecture" if kind == "class" else "other"
