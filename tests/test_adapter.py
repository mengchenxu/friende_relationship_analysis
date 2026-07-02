"""Tests for platform adapters."""

import json
import os
import tempfile

import pytest

from src.adapters.base import Adapter
from src.adapters.testdata import TestDataAdapter
from src.models import Contact, Message, Sender


class TestAdapterInterface:
    """Ensure the ABC contract is enforceable."""

    def test_cannot_instantiate_base_directly(self):
        with pytest.raises(TypeError):
            Adapter()  # type: ignore[abstract]

    def test_subclass_must_implement_parse(self):
        class Broken(Adapter):
            pass

        with pytest.raises(TypeError):
            Broken()  # type: ignore[abstract]

    def test_concrete_adapter_is_valid(self):
        class Good(Adapter):
            def parse(self, file_path: str) -> tuple[list[Contact], list[Message], str]:
                return [], [], "ok"

        g = Good()
        contacts, messages, platform = g.parse("dummy.json")
        assert contacts == []
        assert messages == []
        assert platform == "ok"


class TestTestDataAdapter:
    """End-to-end tests for the Test Data adapter."""

    @pytest.fixture
    def sample_json_path(self):
        """Create a temporary JSON file with known test data."""
        data = {
            "contact_name": "Zhang San",
            "platform": "test",
            "messages": [
                {"sender": "me", "content": "Hey, you free tomorrow?", "timestamp": "2025-01-01T10:00:00"},
                {"sender": "contact", "content": "Yeah, what's up?", "timestamp": "2025-01-01T10:01:30"},
                {"sender": "me", "content": "Wanna grab lunch?", "timestamp": "2025-01-01T10:02:00"},
                {"sender": "contact", "content": "Sure, where?", "timestamp": "2025-01-01T10:03:00"},
                {"sender": "me", "content": "How about that new ramen place?", "timestamp": "2025-01-01T10:04:00"},
                {"sender": "contact", "content": "Sounds good!", "timestamp": "2025-01-01T10:05:00"},
                {"sender": "me", "content": "See you at 12", "timestamp": "2025-01-01T10:06:00"},
                {"sender": "contact", "content": "👍", "timestamp": "2025-01-01T10:07:00"},
            ],
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            path = f.name
        yield path
        os.unlink(path)

    def test_parse_returns_contact(self, sample_json_path):
        adapter = TestDataAdapter()
        contacts, messages, platform = adapter.parse(sample_json_path)

        assert len(contacts) == 1
        assert contacts[0].name == "Zhang San"
        assert contacts[0].platform == "test"
        assert platform == "test"

    def test_parse_returns_messages(self, sample_json_path):
        adapter = TestDataAdapter()
        _, messages, _ = adapter.parse(sample_json_path)

        assert len(messages) == 8
        assert messages[0].content == "Hey, you free tomorrow?"
        assert messages[0].sender == Sender.ME
        assert messages[1].sender == Sender.CONTACT
        assert messages[-1].content == "👍"

    def test_parse_preserves_timestamps(self, sample_json_path):
        adapter = TestDataAdapter()
        _, messages, _ = adapter.parse(sample_json_path)

        from datetime import datetime
        assert messages[0].timestamp == datetime(2025, 1, 1, 10, 0, 0)
        assert messages[-1].timestamp == datetime(2025, 1, 1, 10, 7, 0)
        # Messages must be in chronological order
        for i in range(len(messages) - 1):
            assert messages[i].timestamp <= messages[i + 1].timestamp

    def test_empty_messages_file(self):
        data = {"contact_name": "Nobody", "platform": "test", "messages": []}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            path = f.name

        try:
            adapter = TestDataAdapter()
            contacts, messages, platform = adapter.parse(path)
            assert len(contacts) == 1
            assert contacts[0].name == "Nobody"
            assert messages == []
        finally:
            os.unlink(path)

    def test_missing_contact_name_uses_filename(self):
        data = {"messages": []}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            path = f.name

        try:
            adapter = TestDataAdapter()
            contacts, _, _ = adapter.parse(path)
            # Falls back to filename stem
            assert contacts[0].name != ""
        finally:
            os.unlink(path)
