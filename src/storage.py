"""SQLite storage layer for the relationship analysis application."""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List

from .models import Contact, Conversation, Message, Sender, MessageType


DEFAULT_DB_PATH = os.path.join("data", "relation.db")


class Storage:
    """Wraps sqlite3 to persist Contact, Conversation, and Message records."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """Open (or reopen) the database connection and enable WAL mode."""
        if self._conn is None:
            dirname = os.path.dirname(self.db_path)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def init_db(self):
        """Create tables if they do not already exist."""
        conn = self.connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS contact (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                platform TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                first_msg_time TEXT,
                last_msg_time TEXT,
                FOREIGN KEY (contact_id) REFERENCES contact(id)
            );

            CREATE TABLE IF NOT EXISTS message (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                sender TEXT NOT NULL CHECK(sender IN ('me', 'contact')),
                content TEXT NOT NULL DEFAULT '',
                timestamp TEXT NOT NULL,
                msg_type TEXT NOT NULL DEFAULT 'text',
                FOREIGN KEY (conversation_id) REFERENCES conversation(id)
            );

            CREATE INDEX IF NOT EXISTS idx_message_conv
                ON message(conversation_id, timestamp);
        """)
        conn.commit()

    # ── Contact ────────────────────────────────────────────

    def insert_contact(self, contact: Contact) -> Contact:
        conn = self.connect()
        cur = conn.execute(
            "INSERT INTO contact (name, platform, created_at) VALUES (?, ?, ?)",
            (contact.name, contact.platform, _iso(contact.created_at)),
        )
        conn.commit()
        contact.id = cur.lastrowid
        return contact

    def get_contact(self, contact_id: int) -> Optional[Contact]:
        conn = self.connect()
        row = conn.execute(
            "SELECT id, name, platform, created_at FROM contact WHERE id = ?",
            (contact_id,),
        ).fetchone()
        return _row_to_contact(row) if row else None

    def get_contact_by_name_and_platform(self, name: str, platform: str) -> Optional[Contact]:
        conn = self.connect()
        row = conn.execute(
            "SELECT id, name, platform, created_at FROM contact WHERE name = ? AND platform = ?",
            (name, platform),
        ).fetchone()
        return _row_to_contact(row) if row else None

    def get_or_create_contact(self, name: str, platform: str) -> Contact:
        existing = self.get_contact_by_name_and_platform(name, platform)
        if existing:
            return existing
        return self.insert_contact(Contact(name=name, platform=platform))

    def list_contacts(self) -> List[Contact]:
        conn = self.connect()
        rows = conn.execute(
            "SELECT id, name, platform, created_at FROM contact ORDER BY id"
        ).fetchall()
        return [_row_to_contact(r) for r in rows]

    # ── Conversation ───────────────────────────────────────

    def insert_conversation(self, conv: Conversation) -> Conversation:
        conn = self.connect()
        cur = conn.execute(
            "INSERT INTO conversation (contact_id, message_count, first_msg_time, last_msg_time) "
            "VALUES (?, ?, ?, ?)",
            (conv.contact_id, conv.message_count, _iso(conv.first_msg_time), _iso(conv.last_msg_time)),
        )
        conn.commit()
        conv.id = cur.lastrowid
        return conv

    def get_conversation(self, conv_id: int) -> Optional[Conversation]:
        conn = self.connect()
        row = conn.execute(
            "SELECT id, contact_id, message_count, first_msg_time, last_msg_time "
            "FROM conversation WHERE id = ?",
            (conv_id,),
        ).fetchone()
        return _row_to_conversation(row) if row else None

    def get_conversation_by_contact(self, contact_id: int) -> Optional[Conversation]:
        conn = self.connect()
        row = conn.execute(
            "SELECT id, contact_id, message_count, first_msg_time, last_msg_time "
            "FROM conversation WHERE contact_id = ?",
            (contact_id,),
        ).fetchone()
        return _row_to_conversation(row) if row else None

    def get_or_create_conversation(self, contact_id: int) -> Conversation:
        existing = self.get_conversation_by_contact(contact_id)
        if existing:
            return existing
        return self.insert_conversation(Conversation(contact_id=contact_id))

    def update_conversation_stats(self, conv_id: int):
        """Recalculate message_count, first_msg_time, last_msg_time from messages."""
        conn = self.connect()
        row = conn.execute(
            "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM message WHERE conversation_id = ?",
            (conv_id,),
        ).fetchone()
        conn.execute(
            "UPDATE conversation SET message_count = ?, first_msg_time = ?, last_msg_time = ? WHERE id = ?",
            (row[0], row[1], row[2], conv_id),
        )
        conn.commit()

    # ── Message ────────────────────────────────────────────

    def insert_message(self, msg: Message) -> Message:
        conn = self.connect()
        cur = conn.execute(
            "INSERT INTO message (conversation_id, sender, content, timestamp, msg_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (msg.conversation_id, msg.sender.value, msg.content, _iso(msg.timestamp), msg.msg_type.value),
        )
        conn.commit()
        msg.id = cur.lastrowid
        return msg

    def bulk_insert_messages(self, messages: List[Message]) -> int:
        """Insert many messages in a single transaction. Returns count inserted."""
        if not messages:
            return 0
        conn = self.connect()
        rows = [
            (m.conversation_id, m.sender.value, m.content, _iso(m.timestamp), m.msg_type.value)
            for m in messages
        ]
        conn.executemany(
            "INSERT INTO message (conversation_id, sender, content, timestamp, msg_type) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        return len(rows)

    def get_messages(self, conversation_id: int) -> List[Message]:
        conn = self.connect()
        rows = conn.execute(
            "SELECT id, conversation_id, sender, content, timestamp, msg_type "
            "FROM message WHERE conversation_id = ? ORDER BY timestamp",
            (conversation_id,),
        ).fetchall()
        return [_row_to_message(r) for r in rows]

    def get_messages_by_date_range(
        self, conversation_id: int, start: datetime, end: datetime
    ) -> List[Message]:
        conn = self.connect()
        rows = conn.execute(
            "SELECT id, conversation_id, sender, content, timestamp, msg_type "
            "FROM message WHERE conversation_id = ? AND timestamp >= ? AND timestamp <= ? "
            "ORDER BY timestamp",
            (conversation_id, _iso(start), _iso(end)),
        ).fetchall()
        return [_row_to_message(r) for r in rows]


# ── Row converters ─────────────────────────────────────────

def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _to_dt(val: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(val) if val else None


def _row_to_contact(row) -> Contact:
    return Contact(
        id=row["id"],
        name=row["name"],
        platform=row["platform"],
        created_at=_to_dt(row["created_at"]) or datetime.now(),
    )


def _row_to_conversation(row) -> Conversation:
    return Conversation(
        id=row["id"],
        contact_id=row["contact_id"],
        message_count=row["message_count"],
        first_msg_time=_to_dt(row["first_msg_time"]),
        last_msg_time=_to_dt(row["last_msg_time"]),
    )


def _row_to_message(row) -> Message:
    return Message(
        id=row["id"],
        conversation_id=row["conversation_id"],
        sender=Sender(row["sender"]),
        content=row["content"],
        timestamp=_to_dt(row["timestamp"]) or datetime.now(),
        msg_type=MessageType(row["msg_type"]),
    )
