"""Tests for the Interaction Frequency analysis engine."""

from datetime import datetime, timedelta

import pytest

from src.engine.frequency import analyze_frequency, FrequencyResult
from src.models import Conversation, Message, Sender


def make_msg(content: str, dt: datetime, sender: Sender = Sender.ME) -> Message:
    """Helper to create a Message with minimal boilerplate."""
    return Message(sender=sender, content=content, timestamp=dt)


class TestFrequencyResult:
    """Tests for the FrequencyResult dataclass shape."""

    def test_defaults(self):
        r = FrequencyResult()
        assert r.total_count == 0
        assert r.time_span_days == 0
        assert r.daily_avg == 0.0
        assert r.monthly_trend == []
        assert r.silent_periods == []


class TestAnalyzeFrequency:
    """Tests for the analyze_frequency pure function."""

    # ── basic metrics ────────────────────────────────────

    def test_total_count(self):
        messages = [
            make_msg("a", datetime(2025, 1, 1, 10, 0)),
            make_msg("b", datetime(2025, 1, 1, 10, 1)),
            make_msg("c", datetime(2025, 1, 1, 10, 2)),
        ]
        conv = Conversation(message_count=0)
        result = analyze_frequency(conv, messages)
        assert result.total_count == 3

    def test_time_span_single_day(self):
        messages = [
            make_msg("a", datetime(2025, 1, 1, 10, 0)),
            make_msg("b", datetime(2025, 1, 1, 12, 0)),
        ]
        result = analyze_frequency(Conversation(), messages)
        assert result.time_span_days == 0  # same day

    def test_time_span_multiple_days(self):
        messages = [
            make_msg("a", datetime(2025, 1, 1)),
            make_msg("b", datetime(2025, 1, 10)),
        ]
        result = analyze_frequency(Conversation(), messages)
        assert result.time_span_days == 9

    def test_daily_avg(self):
        messages = [
            make_msg("a", datetime(2025, 1, 1)),
            make_msg("b", datetime(2025, 1, 1)),
            make_msg("c", datetime(2025, 1, 2)),
            make_msg("d", datetime(2025, 1, 2)),
            make_msg("e", datetime(2025, 1, 3)),
            make_msg("f", datetime(2025, 1, 3)),
        ]
        # 6 messages over Jan 1-3 (3 days inclusive → span_days=2, +1 base day)
        result = analyze_frequency(Conversation(), messages)
        assert result.daily_avg == 2.0  # 6 / 3

    # ── monthly trend ────────────────────────────────────

    def test_monthly_trend_single_month(self):
        messages = [
            make_msg("a", datetime(2025, 3, 1)),
            make_msg("b", datetime(2025, 3, 15)),
            make_msg("c", datetime(2025, 3, 31)),
        ]
        result = analyze_frequency(Conversation(), messages)
        assert len(result.monthly_trend) == 1
        assert result.monthly_trend[0]["label"] == "2025-03"
        assert result.monthly_trend[0]["count"] == 3

    def test_monthly_trend_cross_months(self):
        messages = [
            make_msg("a", datetime(2025, 1, 15)),
            make_msg("b", datetime(2025, 1, 20)),
            make_msg("c", datetime(2025, 2, 5)),
            make_msg("d", datetime(2025, 2, 10)),
            make_msg("e", datetime(2025, 3, 1)),
        ]
        result = analyze_frequency(Conversation(), messages)
        assert len(result.monthly_trend) == 3
        assert result.monthly_trend[0] == {"label": "2025-01", "count": 2}
        assert result.monthly_trend[1] == {"label": "2025-02", "count": 2}
        assert result.monthly_trend[2] == {"label": "2025-03", "count": 1}

    def test_monthly_trend_fills_gaps(self):
        """Months with zero messages should still appear in the trend."""
        messages = [
            make_msg("a", datetime(2025, 1, 1)),
            make_msg("b", datetime(2025, 4, 1)),
        ]
        result = analyze_frequency(Conversation(), messages)
        labels = [m["label"] for m in result.monthly_trend]
        assert labels == ["2025-01", "2025-02", "2025-03", "2025-04"]
        counts = [m["count"] for m in result.monthly_trend]
        assert counts == [1, 0, 0, 1]

    # ── silent periods ───────────────────────────────────

    def test_no_silent_periods_when_frequent(self):
        messages = [
            make_msg("a", datetime(2025, 1, 1)),
            make_msg("b", datetime(2025, 1, 3)),
            make_msg("c", datetime(2025, 1, 5)),
        ]
        result = analyze_frequency(Conversation(), messages, silence_days=7)
        assert len(result.silent_periods) == 0

    def test_detects_silent_period(self):
        messages = [
            make_msg("a", datetime(2025, 1, 1)),
            make_msg("b", datetime(2025, 1, 15)),  # 14-day gap
        ]
        result = analyze_frequency(Conversation(), messages, silence_days=7)
        assert len(result.silent_periods) == 1
        sp = result.silent_periods[0]
        assert sp["start"] == "2025-01-01"
        assert sp["end"] == "2025-01-15"
        assert sp["days"] == 14

    def test_multiple_silent_periods(self):
        messages = [
            make_msg("a", datetime(2025, 1, 1)),
            make_msg("b", datetime(2025, 1, 20)),   # gap 1: 19 days
            make_msg("c", datetime(2025, 1, 22)),
            make_msg("d", datetime(2025, 3, 1)),     # gap 2: 38 days
        ]
        result = analyze_frequency(Conversation(), messages, silence_days=7)
        assert len(result.silent_periods) == 2
        assert result.silent_periods[0]["days"] == 19
        assert result.silent_periods[1]["days"] == 38

    def test_custom_silence_threshold(self):
        messages = [
            make_msg("a", datetime(2025, 1, 1)),
            make_msg("b", datetime(2025, 1, 5)),   # 4-day gap
        ]
        result_default = analyze_frequency(Conversation(), messages, silence_days=7)
        assert len(result_default.silent_periods) == 0

        result_custom = analyze_frequency(Conversation(), messages, silence_days=3)
        assert len(result_custom.silent_periods) == 1
        assert result_custom.silent_periods[0]["days"] == 4

    # ── edge cases ───────────────────────────────────────

    def test_empty_messages(self):
        result = analyze_frequency(Conversation(), [])
        assert result.total_count == 0
        assert result.time_span_days == 0
        assert result.daily_avg == 0.0
        assert result.monthly_trend == []
        assert result.silent_periods == []

    def test_single_message(self):
        messages = [make_msg("only", datetime(2025, 6, 15))]
        result = analyze_frequency(Conversation(), messages)
        assert result.total_count == 1
        assert result.time_span_days == 0
        assert result.daily_avg == 1.0
        assert len(result.monthly_trend) == 1
        assert result.monthly_trend[0]["count"] == 1
        assert result.silent_periods == []

    def test_conversation_with_stats_also_works(self):
        """analyze_frequency should work even if the Conversation has pre-stats."""
        messages = [
            make_msg("a", datetime(2025, 1, 1)),
            make_msg("b", datetime(2025, 1, 2)),
        ]
        conv = Conversation(
            message_count=99,
            first_msg_time=datetime(2024, 1, 1),
            last_msg_time=datetime(2024, 12, 31),
        )
        result = analyze_frequency(conv, messages)
        # It uses messages, not conv stats
        assert result.total_count == 2
        assert result.time_span_days == 1
