"""Interaction Frequency analysis engine — pure functions, no I/O."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from ..models import Conversation, Message


@dataclass
class FrequencyResult:
    """The output of frequency analysis for one Conversation."""

    total_count: int = 0
    time_span_days: int = 0
    daily_avg: float = 0.0
    monthly_trend: list[dict] = field(default_factory=list)
    silent_periods: list[dict] = field(default_factory=list)


def analyze_frequency(
    conversation: Conversation,
    messages: list[Message],
    silence_days: int = 7,
) -> FrequencyResult:
    """Analyse interaction frequency from a set of Messages.

    Args:
        conversation: The Conversation container (unused — kept for future extensibility).
        messages: All messages belonging to this Conversation, in any order.
        silence_days: Gaps longer than this many calendar days are flagged as silent periods.

    Returns:
        A FrequencyResult with computed metrics.
    """
    if not messages:
        return FrequencyResult()

    sorted_msgs = sorted(messages, key=lambda m: m.timestamp)
    first = sorted_msgs[0].timestamp
    last = sorted_msgs[-1].timestamp

    # ── basic counts ─────────────────────────────────────
    total_count = len(sorted_msgs)
    first_date = first.date()
    last_date = last.date()
    time_span_days = (last_date - first_date).days
    calendar_days = time_span_days + 1  # inclusive of both ends
    daily_avg = round(total_count / calendar_days, 2)

    # ── monthly trend ────────────────────────────────────
    monthly_trend = _build_monthly_trend(sorted_msgs, first_date, last_date)

    # ── silent periods ───────────────────────────────────
    silent_periods = _detect_silent_periods(sorted_msgs, silence_days)

    return FrequencyResult(
        total_count=total_count,
        time_span_days=time_span_days,
        daily_avg=daily_avg,
        monthly_trend=monthly_trend,
        silent_periods=silent_periods,
    )


def _build_monthly_trend(
    messages: list[Message],
    first_date,
    last_date,
) -> list[dict]:
    """Count messages per calendar month, filling zero-count months."""
    monthly: dict[str, int] = {}
    for m in messages:
        key = m.timestamp.strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + 1

    # Fill every month between first_date and last_date
    trend = []
    current = first_date.replace(day=1)
    end_month = last_date.replace(day=1)
    while current <= end_month:
        label = current.strftime("%Y-%m")
        trend.append({"label": label, "count": monthly.get(label, 0)})
        # Advance one month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return trend


def _detect_silent_periods(
    messages: list[Message],
    silence_days: int,
) -> list[dict]:
    """Find gaps between consecutive messages that exceed the silence threshold."""
    periods = []
    for i in range(len(messages) - 1):
        d1 = messages[i].timestamp.date()
        d2 = messages[i + 1].timestamp.date()
        gap = (d2 - d1).days
        if gap > silence_days:
            periods.append({
                "start": d1.isoformat(),
                "end": d2.isoformat(),
                "days": gap,
            })
    return periods
