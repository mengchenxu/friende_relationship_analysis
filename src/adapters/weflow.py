"""WeFlow adapter — parses WeFlow JSON export into the internal data model."""

import json
from datetime import datetime
from typing import Any

from .base import Adapter
from ..models import Contact, Message, Sender, MessageType

# Mapping from WeFlow message types to our internal MessageType
_TYPE_MAP: dict[str, MessageType] = {
    "文本消息": MessageType.TEXT,
    "图片消息": MessageType.IMAGE,
    "语音消息": MessageType.AUDIO,
    "视频消息": MessageType.VIDEO,
    "文件消息": MessageType.FILE,
    "链接消息": MessageType.OTHER,
    "表情": MessageType.TEXT,       # treat sticker text as text
}

_SKIP_TYPES = {"系统消息"}


class WeFlowAdapter(Adapter):
    """Parses a WeFlow JSON export file.

    Expected structure::

        {
          "weflow": {"version": "...", "exportedAt": ...},
          "session": {
            "nickname": "...",
            "remark": "...",
            "displayName": "...",
            "type": "私聊",
            ...
          },
          "messages": [
            {
              "localId": 1,
              "formattedTime": "2026-06-11 22:53:25",
              "type": "文本消息",
              "content": "...",
              "isSend": 0,
              ...
            }
          ]
        }

    ``isSend``: 1 = sent by the user (me), 0 = received from the contact.
    """

    def parse(self, file_path: str) -> tuple[list[Contact], list[Message], str]:
        with open(file_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)

        session = data.get("session", {})
        platform = "wechat"

        # Contact name: prefer remark, then nickname, then displayName
        contact_name = session.get("remark") or session.get("nickname") or session.get("displayName") or "Unknown"

        contact = Contact(name=contact_name, platform=platform)

        messages: list[Message] = []
        for raw in data.get("messages", []):
            msg_type_str = raw.get("type", "")

            # Skip system messages
            if msg_type_str in _SKIP_TYPES:
                continue

            msg_type = _TYPE_MAP.get(msg_type_str, MessageType.TEXT)
            sender = Sender.ME if raw.get("isSend") == 1 else Sender.CONTACT
            content = raw.get("content", "")

            # Parse timestamp from formattedTime
            ts_str = raw.get("formattedTime", "")
            try:
                timestamp = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue  # skip malformed timestamps

            messages.append(Message(
                sender=sender,
                content=content,
                timestamp=timestamp,
                msg_type=msg_type,
            ))

        return [contact], messages, platform
