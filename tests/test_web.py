"""Integration tests for web routes using TestClient."""

import pytest
from fastapi.testclient import TestClient

from src.storage import Storage
from src.web.app import app


@pytest.fixture
def client():
    """Provide a TestClient with an in-memory storage backend."""
    storage = Storage(":memory:")
    storage.connect()
    storage.init_db()

    # Override the app's storage for the test
    app.state.storage = storage

    with TestClient(app) as c:
        yield c
    storage.close()


class TestHomePage:
    def test_renders_when_empty(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "No contacts imported yet" in response.text

    def test_shows_contact_after_import(self, client):
        storage = app.state.storage
        c = storage.insert_contact(storage.get_or_create_contact("Test User", "test"))
        conv = storage.insert_conversation(
            storage.get_or_create_conversation(c.id)
        )

        response = client.get("/")
        assert response.status_code == 200
        assert "Test User" in response.text


class TestImportPage:
    def test_renders(self, client):
        response = client.get("/import")
        assert response.status_code == 200
        assert "Import" in response.text


class TestContactDetail:
    def test_renders_for_existing_contact(self, client):
        storage = app.state.storage
        c = storage.insert_contact(storage.get_or_create_contact("Detail Test", "test"))
        conv = storage.insert_conversation(storage.get_or_create_conversation(c.id))

        response = client.get(f"/contact/{c.id}")
        assert response.status_code == 200
        assert "Detail Test" in response.text

    def test_404_for_missing_contact(self, client):
        response = client.get("/contact/999")
        assert response.status_code == 404
