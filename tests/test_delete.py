"""Tests for delete operations."""

import pytest
from datetime import datetime

from src.models import Contact, Conversation, Message, Sender
from src.storage import Storage


@pytest.fixture
def storage():
    s = Storage(":memory:")
    s.connect()
    s.init_db()
    yield s
    s.close()


class TestDeleteContact:
    def test_cascade_deletes_conversation_and_messages(self, storage):
        c = storage.insert_contact(Contact(name="ToDelete", platform="test"))
        conv = storage.insert_conversation(Conversation(contact_id=c.id))
        storage.bulk_insert_messages([
            Message(conversation_id=conv.id, sender=Sender.ME,
                    content="a", timestamp=datetime(2025, 1, 1)),
            Message(conversation_id=conv.id, sender=Sender.CONTACT,
                    content="b", timestamp=datetime(2025, 1, 2)),
        ])
        storage.update_conversation_stats(conv.id)

        storage.delete_contact(c.id)

        assert storage.get_contact(c.id) is None
        assert storage.get_conversation(conv.id) is None
        assert storage.get_messages(conv.id) == []

    def test_delete_contact_without_conversation(self, storage):
        c = storage.insert_contact(Contact(name="Solo", platform="test"))
        storage.delete_contact(c.id)
        assert storage.get_contact(c.id) is None

    def test_other_contacts_unaffected(self, storage):
        c1 = storage.insert_contact(Contact(name="A", platform="test"))
        c2 = storage.insert_contact(Contact(name="B", platform="test"))

        storage.delete_contact(c1.id)

        assert storage.get_contact(c1.id) is None
        assert storage.get_contact(c2.id) is not None


class TestClearAll:
    def test_clears_everything(self, storage):
        c1 = storage.insert_contact(Contact(name="X", platform="test"))
        c2 = storage.insert_contact(Contact(name="Y", platform="test"))
        conv1 = storage.insert_conversation(Conversation(contact_id=c1.id))
        conv2 = storage.insert_conversation(Conversation(contact_id=c2.id))
        storage.bulk_insert_messages([
            Message(conversation_id=conv1.id, sender=Sender.ME,
                    content="x", timestamp=datetime(2025, 1, 1)),
            Message(conversation_id=conv2.id, sender=Sender.ME,
                    content="y", timestamp=datetime(2025, 1, 1)),
        ])

        storage.clear_all()

        assert storage.list_contacts() == []
        assert storage.get_messages(conv1.id) == []
        assert storage.get_messages(conv2.id) == []

    def test_clear_all_idempotent(self, storage):
        storage.clear_all()
        storage.clear_all()  # should not crash
        assert storage.list_contacts() == []
