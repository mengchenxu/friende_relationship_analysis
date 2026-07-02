"""Tests for the Storage layer using in-memory SQLite."""

import pytest
from datetime import datetime

from src.models import Contact, Conversation, Message, Sender, MessageType
from src.storage import Storage


@pytest.fixture
def storage():
    """Provide a Storage instance backed by :memory: for isolated tests."""
    s = Storage(":memory:")
    s.connect()
    s.init_db()
    yield s
    s.close()


class TestContact:
    def test_insert_and_get(self, storage):
        c = storage.insert_contact(Contact(name="Zhang San", platform="test"))
        assert c.id == 1
        fetched = storage.get_contact(c.id)
        assert fetched.name == "Zhang San"
        assert fetched.platform == "test"

    def test_get_or_create_inserts_once(self, storage):
        c1 = storage.get_or_create_contact("Li Si", "test")
        c2 = storage.get_or_create_contact("Li Si", "test")
        assert c1.id == c2.id
        assert len(storage.list_contacts()) == 1

    def test_list_contacts(self, storage):
        storage.insert_contact(Contact(name="A", platform="p"))
        storage.insert_contact(Contact(name="B", platform="p"))
        assert len(storage.list_contacts()) == 2


class TestConversation:
    def test_insert_and_get(self, storage):
        contact = storage.insert_contact(Contact(name="Wang Wu", platform="test"))
        conv = storage.insert_conversation(Conversation(contact_id=contact.id))
        assert conv.id == 1
        fetched = storage.get_conversation(conv.id)
        assert fetched.contact_id == contact.id

    def test_get_or_create_inserts_once(self, storage):
        contact = storage.insert_contact(Contact(name="Zhao Liu", platform="test"))
        conv1 = storage.get_or_create_conversation(contact.id)
        conv2 = storage.get_or_create_conversation(contact.id)
        assert conv1.id == conv2.id

    def test_update_stats(self, storage):
        contact = storage.insert_contact(Contact(name="Qian Qi", platform="test"))
        conv = storage.insert_conversation(Conversation(contact_id=contact.id))
        t1 = datetime(2025, 1, 1, 10, 0, 0)
        t2 = datetime(2025, 1, 3, 10, 0, 0)
        storage.bulk_insert_messages([
            Message(conversation_id=conv.id, sender=Sender.ME, content="hi", timestamp=t1),
            Message(conversation_id=conv.id, sender=Sender.CONTACT, content="hey", timestamp=t2),
        ])
        storage.update_conversation_stats(conv.id)
        updated = storage.get_conversation(conv.id)
        assert updated.message_count == 2
        assert updated.first_msg_time == t1
        assert updated.last_msg_time == t2


class TestMessage:
    def test_insert_single(self, storage):
        contact = storage.insert_contact(Contact(name="Sun Ba", platform="test"))
        conv = storage.insert_conversation(Conversation(contact_id=contact.id))
        msg = storage.insert_message(Message(
            conversation_id=conv.id,
            sender=Sender.ME,
            content="Hello",
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
        ))
        assert msg.id == 1

    def test_bulk_insert(self, storage):
        contact = storage.insert_contact(Contact(name="Zhou Jiu", platform="test"))
        conv = storage.insert_conversation(Conversation(contact_id=contact.id))
        count = storage.bulk_insert_messages([
            Message(conversation_id=conv.id, sender=Sender.ME, content="a",
                    timestamp=datetime(2025, 1, 1, 10, 0, 0)),
            Message(conversation_id=conv.id, sender=Sender.CONTACT, content="b",
                    timestamp=datetime(2025, 1, 1, 10, 1, 0)),
            Message(conversation_id=conv.id, sender=Sender.ME, content="c",
                    timestamp=datetime(2025, 1, 1, 10, 2, 0)),
        ])
        assert count == 3
        msgs = storage.get_messages(conv.id)
        assert len(msgs) == 3
        assert msgs[0].content == "a"
        assert msgs[1].sender == Sender.CONTACT

    def test_bulk_insert_empty(self, storage):
        assert storage.bulk_insert_messages([]) == 0

    def test_get_messages_by_date_range(self, storage):
        contact = storage.insert_contact(Contact(name="Wu Shi", platform="test"))
        conv = storage.insert_conversation(Conversation(contact_id=contact.id))
        storage.bulk_insert_messages([
            Message(conversation_id=conv.id, sender=Sender.ME, content="m1",
                    timestamp=datetime(2025, 1, 1)),
            Message(conversation_id=conv.id, sender=Sender.ME, content="m2",
                    timestamp=datetime(2025, 2, 1)),
            Message(conversation_id=conv.id, sender=Sender.ME, content="m3",
                    timestamp=datetime(2025, 3, 1)),
        ])
        filtered = storage.get_messages_by_date_range(
            conv.id,
            datetime(2025, 1, 15),
            datetime(2025, 3, 15),
        )
        assert len(filtered) == 2
        assert filtered[0].content == "m2"
