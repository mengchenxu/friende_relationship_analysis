"""Integration tests for web routes using TestClient."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from src.storage import Storage
from src.web.app import app


@pytest.fixture
def client():
    """Provide a TestClient backed by a unique temp-file DB for full isolation."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_")
    os.close(fd)

    with TestClient(app) as c:
        # Replace the lifespan-created storage (data/relation.db) with our isolated one.
        # Must happen AFTER TestClient because the lifespan runs during TestClient init.
        if hasattr(app.state, "storage"):
            app.state.storage.close()
        storage = Storage(path)
        storage.connect()
        storage.init_db()
        app.state.storage = storage
        yield c
        storage.close()

    os.unlink(path)


class TestHomePage:
    def test_renders_when_empty(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "暂无联系人" in response.text

    def test_shows_contact_after_import(self, client):
        storage = app.state.storage
        storage.get_or_create_contact("Test User", "test")
        storage.get_or_create_conversation(1)

        response = client.get("/")
        assert response.status_code == 200
        assert "Test User" in response.text


class TestImportPage:
    def test_renders(self, client):
        response = client.get("/import")
        assert response.status_code == 200
        assert "导入" in response.text


class TestContactDetail:
    def test_renders_for_existing_contact(self, client):
        storage = app.state.storage
        c = storage.get_or_create_contact("Detail Test", "test")
        conv = storage.get_or_create_conversation(c.id)

        response = client.get(f"/contact/{c.id}")
        assert response.status_code == 200
        assert "Detail Test" in response.text

    def test_404_for_missing_contact(self, client):
        response = client.get("/contact/999")
        assert response.status_code == 404
