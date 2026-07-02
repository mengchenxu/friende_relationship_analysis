"""Abstract base class for chat-platform adapters."""

from abc import ABC, abstractmethod

from ..models import Contact, Message


class Adapter(ABC):
    """Convert a platform-specific chat export into the internal data model.

    Each concrete adapter handles one platform (WeChat, QQ, Telegram, test data, etc.).
    """

    @abstractmethod
    def parse(self, file_path: str) -> tuple[list[Contact], list[Message], str]:
        """Parse a chat export file and return (contacts, messages, platform_name).

        The caller is responsible for mapping the returned Contacts and Messages
        into Conversations and persisting them via Storage.
        """
        ...
