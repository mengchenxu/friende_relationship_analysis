"""Tests for the Reciprocity (relationship balance) analysis engine."""

from datetime import datetime, timedelta

import pytest

from src.engine.reciprocity import analyze_reciprocity, ReciprocityResult
from src.models import Conversation, Message, Sender


def msg(sender: Sender, content: str, dt: datetime) -> Message:
    return Message(sender=sender, content=content, timestamp=dt)


class TestReciprocityResult:
    def test_defaults(self):
        r = ReciprocityResult()
        assert r.me_initiation_rate == 0.0
        assert r.contact_initiation_rate == 0.0
        assert r.me_reply_avg_seconds == 0.0
        assert r.contact_reply_avg_seconds == 0.0
        assert r.me_avg_length == 0.0
        assert r.contact_avg_length == 0.0
        assert r.me_closure_rate == 0.0
        assert r.contact_closure_rate == 0.0


class TestAnalyzeReciprocity:
    """Tests for the analyze_reciprocity pure function."""

    base = datetime(2025, 1, 1, 10, 0, 0)

    # ── initiation ───────────────────────────────────────

    def test_initiation_balanced(self):
        """Two sessions, each party starts one → 50/50."""
        messages = [
            msg(Sender.ME,      "a", self.base),                          # session 1: me starts
            msg(Sender.CONTACT, "b", self.base + timedelta(minutes=5)),
            msg(Sender.CONTACT, "c", self.base + timedelta(hours=8)),      # session 2: contact starts
            msg(Sender.ME,      "d", self.base + timedelta(hours=8, minutes=5)),
        ]
        r = analyze_reciprocity(Conversation(), messages)
        assert r.me_initiation_rate == 0.5
        assert r.contact_initiation_rate == 0.5

    def test_initiation_one_sided(self):
        """One session, started by me."""
        messages = [
            msg(Sender.ME,      "a", self.base),
            msg(Sender.CONTACT, "b", self.base + timedelta(minutes=5)),
        ]
        r = analyze_reciprocity(Conversation(), messages)
        assert r.me_initiation_rate == 1.0
        assert r.contact_initiation_rate == 0.0

    # ── reply time ───────────────────────────────────────

    def test_reply_time_balanced(self):
        """Both reply after 2 minutes."""
        messages = [
            msg(Sender.ME,      "a", self.base),
            msg(Sender.CONTACT, "b", self.base + timedelta(minutes=2)),
            msg(Sender.ME,      "c", self.base + timedelta(minutes=4)),
        ]
        r = analyze_reciprocity(Conversation(), messages)
        # Contact replied in 120s, me replied in 120s
        assert r.contact_reply_avg_seconds == pytest.approx(120, abs=1)
        assert r.me_reply_avg_seconds == pytest.approx(120, abs=1)

    def test_reply_time_one_faster(self):
        """I reply fast (1m), contact replies slow (10m)."""
        messages = [
            msg(Sender.ME,      "a", self.base),
            msg(Sender.CONTACT, "b", self.base + timedelta(minutes=10)),
            msg(Sender.ME,      "c", self.base + timedelta(minutes=11)),
        ]
        r = analyze_reciprocity(Conversation(), messages)
        assert r.contact_reply_avg_seconds == pytest.approx(600, abs=1)
        assert r.me_reply_avg_seconds == pytest.approx(60, abs=1)

    def test_reply_time_no_responses(self):
        """Only one message — nobody replied, so reply times are 0."""
        messages = [msg(Sender.ME, "a", self.base)]
        r = analyze_reciprocity(Conversation(), messages)
        assert r.me_reply_avg_seconds == 0.0
        assert r.contact_reply_avg_seconds == 0.0

    # ── message length ───────────────────────────────────

    def test_message_length(self):
        messages = [
            msg(Sender.ME,      "hello world", self.base),           # 11 chars
            msg(Sender.CONTACT, "hi",          self.base + timedelta(minutes=1)),  # 2 chars
        ]
        r = analyze_reciprocity(Conversation(), messages)
        assert r.me_avg_length == 11.0
        assert r.contact_avg_length == 2.0

    def test_message_length_no_messages_from_one_side(self):
        """All messages from me — contact average should be 0."""
        messages = [
            msg(Sender.ME, "a", self.base),
            msg(Sender.ME, "bb", self.base + timedelta(minutes=1)),
        ]
        r = analyze_reciprocity(Conversation(), messages)
        assert r.me_avg_length == 1.5
        assert r.contact_avg_length == 0.0

    # ── closure ──────────────────────────────────────────

    def test_closure_balanced(self):
        """Two sessions, each party closes one → 50/50."""
        messages = [
            msg(Sender.ME,      "a", self.base),                          # session 1: me starts
            msg(Sender.CONTACT, "b", self.base + timedelta(minutes=5)),   # contact closes
            msg(Sender.CONTACT, "c", self.base + timedelta(hours=8)),      # session 2: contact starts
            msg(Sender.ME,      "d", self.base + timedelta(hours=8, minutes=5)),  # me closes
        ]
        r = analyze_reciprocity(Conversation(), messages)
        assert r.me_closure_rate == 0.5
        assert r.contact_closure_rate == 0.5

    # ── edge cases ───────────────────────────────────────

    def test_empty_messages(self):
        r = analyze_reciprocity(Conversation(), [])
        assert r.me_initiation_rate == 0.0
        assert r.me_closure_rate == 0.0

    def test_single_message(self):
        messages = [msg(Sender.ME, "hello", self.base)]
        r = analyze_reciprocity(Conversation(), messages)
        assert r.me_initiation_rate == 1.0
        assert r.me_closure_rate == 1.0
        assert r.me_avg_length == 5.0

    def test_consecutive_same_sender_no_replies(self):
        """When same sender sends consecutively, no reply times are recorded."""
        messages = [
            msg(Sender.ME, "first",  self.base),
            msg(Sender.ME, "second", self.base + timedelta(minutes=1)),
            msg(Sender.ME, "third",  self.base + timedelta(minutes=2)),
        ]
        r = analyze_reciprocity(Conversation(), messages)
        # Only one session, started and closed by me
        assert r.me_initiation_rate == 1.0
        assert r.me_closure_rate == 1.0
        # No replies from contact to measure
        assert r.contact_reply_avg_seconds == 0.0
        # No replies from me either (since contact never sent)
        assert r.me_reply_avg_seconds == 0.0
