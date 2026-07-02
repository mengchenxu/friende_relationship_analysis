"""Test-data adapter — parses a simple JSON format for development and testing."""

import json
import os
from datetime import datetime
from typing import Any

from .base import Adapter
from ..models import Contact, Message, Sender


class TestDataAdapter(Adapter):
    """Parses a hand-crafted JSON file into the internal data model.

    Expected JSON format::

        {
            "contact_name": "Zhang San",
            "platform": "test",
            "messages": [
                {"sender": "me", "content": "Hello", "timestamp": "2025-01-01T10:00:00"},
                {"sender": "contact", "content": "Hi!",   "timestamp": "2025-01-01T10:01:00"}
            ]
        }

    - ``contact_name`` is optional; falls back to the filename stem.
    - ``platform`` defaults to ``"test"``.
    - ``sender`` must be ``"me"`` or ``"contact"``.
    - ``timestamp`` must be ISO-8601.
    """

    def parse(self, file_path: str) -> tuple[list[Contact], list[Message], str]:
        with open(file_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)

        platform = data.get("platform", "test")
        contact_name = data.get("contact_name") or _fallback_name(file_path)

        contact = Contact(name=contact_name, platform=platform)
        messages = [_parse_message(m) for m in data.get("messages", [])]

        # Ensure chronological order
        messages.sort(key=lambda m: m.timestamp)

        return [contact], messages, platform


def _fallback_name(file_path: str) -> str:
    """Derive a contact name from the filename when none is provided."""
    stem = os.path.splitext(os.path.basename(file_path))[0]
    return stem if stem else "Unknown"


def _parse_message(raw: dict[str, str]) -> Message:
    sender = Sender(raw["sender"])
    return Message(
        sender=sender,
        content=raw.get("content", ""),
        timestamp=datetime.fromisoformat(raw["timestamp"]),
    )
