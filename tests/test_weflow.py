"""Tests for the WeFlow adapter."""

import json
import os
import tempfile
from datetime import datetime

import pytest

from src.adapters.weflow import WeFlowAdapter
from src.models import Sender, MessageType


@pytest.fixture
def weflow_file():
    data = {
        "weflow": {"version": "1.0.3", "exportedAt": 1782970501, "generator": "WeFlow"},
        "session": {
            "wxid": "test_wxid",
            "nickname": "Xiao Ming",
            "remark": "小明",
            "displayName": "小明",
            "type": "私聊",
        },
        "messages": [
            {"localId": 1, "formattedTime": "2026-06-11 22:53:25", "type": "系统消息",
             "content": "以上是打招呼的消息", "isSend": 0},
            {"localId": 2, "formattedTime": "2026-06-11 22:54:00", "type": "文本消息",
             "content": "我通过了你的朋友验证请求", "isSend": 0},
            {"localId": 3, "formattedTime": "2026-06-11 22:57:46", "type": "文本消息",
             "content": "在不在", "isSend": 0},
            {"localId": 4, "formattedTime": "2026-06-11 22:58:00", "type": "文本消息",
             "content": "在的，什么事", "isSend": 1},
            {"localId": 5, "formattedTime": "2026-06-11 22:59:00", "type": "图片消息",
             "content": "[图片]", "isSend": 0},
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
        path = f.name
    yield path
    os.unlink(path)


class TestWeFlowAdapter:
    def test_contact_name_uses_remark(self, weflow_file):
        contacts, _, _ = WeFlowAdapter().parse(weflow_file)
        assert contacts[0].name == "小明"
        assert contacts[0].platform == "wechat"

    def test_skips_system_messages(self, weflow_file):
        _, messages, _ = WeFlowAdapter().parse(weflow_file)
        assert len(messages) == 4

    def test_is_send_maps_to_sender(self, weflow_file):
        _, messages, _ = WeFlowAdapter().parse(weflow_file)
        assert messages[0].sender == Sender.CONTACT  # isSend=0
        assert messages[2].sender == Sender.ME        # isSend=1

    def test_message_types_mapped(self, weflow_file):
        _, messages, _ = WeFlowAdapter().parse(weflow_file)
        assert messages[0].msg_type == MessageType.TEXT
        assert messages[-1].msg_type == MessageType.IMAGE

    def test_timestamps_parsed(self, weflow_file):
        _, messages, _ = WeFlowAdapter().parse(weflow_file)
        assert messages[0].timestamp == datetime(2026, 6, 11, 22, 54, 0)

    def test_platform_is_wechat(self, weflow_file):
        _, _, platform = WeFlowAdapter().parse(weflow_file)
        assert platform == "wechat"

    def test_fallback_to_nickname(self):
        data = {
            "weflow": {"version": "1.0"},
            "session": {"nickname": "NoRemark", "remark": "", "type": "私聊"},
            "messages": [],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            path = f.name
        try:
            contacts, _, _ = WeFlowAdapter().parse(path)
            assert contacts[0].name == "NoRemark"
        finally:
            os.unlink(path)

    def test_empty_messages(self):
        data = {
            "weflow": {"version": "1.0"},
            "session": {"nickname": "Someone", "type": "私聊"},
            "messages": [],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            path = f.name
        try:
            _, messages, _ = WeFlowAdapter().parse(path)
            assert messages == []
        finally:
            os.unlink(path)
