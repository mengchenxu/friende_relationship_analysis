"""Core data models for the relationship analysis application."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Sender(Enum):
    ME = "me"
    CONTACT = "contact"


class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"
    OTHER = "other"


@dataclass
class Contact:
    """A person who participates in conversations."""

    id: Optional[int] = None
    name: str = ""
    platform: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Conversation:
    """A container holding all messages between two Contacts (one-on-one only)."""

    id: Optional[int] = None
    contact_id: int = 0
    message_count: int = 0
    first_msg_time: Optional[datetime] = None
    last_msg_time: Optional[datetime] = None


@dataclass
class Message:
    """A single message within a Conversation."""

    id: Optional[int] = None
    conversation_id: int = 0
    sender: Sender = Sender.ME
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    msg_type: MessageType = MessageType.TEXT
