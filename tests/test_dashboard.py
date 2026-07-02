"""Integration tests for the dashboard comparison page."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from src.storage import Storage
from src.web.app import app
from src.models import Message, Sender, Conversation, Contact
from datetime import datetime


@pytest.fixture
def client():
    """Provide a TestClient backed by a unique temp-file DB."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_")
    os.close(fd)

    with TestClient(app) as c:
        if hasattr(app.state, "storage"):
            app.state.storage.close()
        storage = Storage(path)
        storage.connect()
        storage.init_db()
        app.state.storage = storage
        yield c
        storage.close()
    os.unlink(path)


class TestDashboard:
    def test_renders_when_empty(self, client):
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "对比面板" in response.text

    def test_renders_with_single_contact(self, client):
        storage = app.state.storage
        c = storage.get_or_create_contact("Only One", "test")
        conv = storage.get_or_create_conversation(c.id)
        storage.bulk_insert_messages([
            Message(conversation_id=conv.id, sender=Sender.ME,
                    content="hello", timestamp=datetime(2025, 1, 1)),
        ])
        storage.update_conversation_stats(conv.id)

        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "Only One" in response.text

    def test_shows_all_contacts(self, client):
        storage = app.state.storage
        for name in ["Alpha", "Beta", "Gamma"]:
            contact = storage.get_or_create_contact(name, "test")
            conv = storage.get_or_create_conversation(contact.id)
            storage.bulk_insert_messages([
                Message(conversation_id=conv.id, sender=Sender.ME,
                        content="x", timestamp=datetime(2025, 1, 1)),
                Message(conversation_id=conv.id, sender=Sender.CONTACT,
                        content="y", timestamp=datetime(2025, 1, 2)),
            ])
            storage.update_conversation_stats(conv.id)

        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "Alpha" in response.text
        assert "Beta" in response.text
        assert "Gamma" in response.text

    def test_navigation_links_present(self, client):
        """Dashboard and home should link to each other."""
        response = client.get("/dashboard")
        assert 'href="/"' in response.text  # back to home

        response = client.get("/")
        assert 'href="/dashboard"' in response.text  # link to dashboard
