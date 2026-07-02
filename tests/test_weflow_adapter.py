"""Tests for the WeFlow adapter."""

import json
import os
import tempfile

import pytest

from src.adapters.weflow import WeFlowAdapter
from src.models import Sender


@pytest.fixture
def sample_weflow_path():
    """Create a minimal WeFlow-format JSON file."""
    data = {
        "weflow": {"version": "1.0.3", "exportedAt": 1782970501},
        "session": {
            "nickname": "Xiao Ming",
            "remark": "小明",
            "displayName": "小明",
            "type": "私聊",
        },
        "messages": [
            {
                "localId": 1,
                "formattedTime": "2026-06-11 10:00:00",
                "type": "文本消息",
                "content": "你好",
                "isSend": 0,
            },
            {
                "localId": 2,
                "formattedTime": "2026-06-11 10:01:00",
                "type": "文本消息",
                "content": "Hello!",
                "isSend": 1,
            },
            {
                "localId": 3,
                "formattedTime": "2026-06-11 10:02:00",
                "type": "系统消息",
                "content": "以上是打招呼的消息",
                "isSend": 0,
            },
        ],
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(data, f, ensure_ascii=False)
        path = f.name
    yield path
    os.unlink(path)


class TestWeFlowAdapter:
    def test_parses_contact_name(self, sample_weflow_path):
        adapter = WeFlowAdapter()
        contacts, _, _ = adapter.parse(sample_weflow_path)
        assert len(contacts) == 1
        # remark takes priority
        assert contacts[0].name == "小明"
        assert contacts[0].platform == "wechat"

    def test_skips_system_messages(self, sample_weflow_path):
        adapter = WeFlowAdapter()
        _, messages, _ = adapter.parse(sample_weflow_path)
        assert len(messages) == 2  # 3 messages minus 1 system message

    def test_maps_is_send_correctly(self, sample_weflow_path):
        adapter = WeFlowAdapter()
        _, messages, _ = adapter.parse(sample_weflow_path)
        assert messages[0].sender == Sender.CONTACT   # isSend=0
        assert messages[1].sender == Sender.ME         # isSend=1

    def test_parses_remark_fallback(self):
        data = {
            "weflow": {"version": "1.0"},
            "session": {"nickname": "nick_name"},
            "messages": [],
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f, ensure_ascii=False)
            path = f.name
        try:
            adapter = WeFlowAdapter()
            contacts, _, _ = adapter.parse(path)
            assert contacts[0].name == "nick_name"
        finally:
            os.unlink(path)
