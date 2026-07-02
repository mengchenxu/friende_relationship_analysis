"""Reciprocity analysis engine — measures conversation balance. Pure functions."""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional

from ..models import Conversation, Message, Sender


DEFAULT_SESSION_GAP_HOURS = 6


@dataclass
class ReciprocityResult:
    """How balanced is the conversation between two parties?"""

    me_initiation_rate: float = 0.0
    contact_initiation_rate: float = 0.0
    me_reply_avg_seconds: float = 0.0
    contact_reply_avg_seconds: float = 0.0
    me_avg_length: float = 0.0
    contact_avg_length: float = 0.0
    me_closure_rate: float = 0.0
    contact_closure_rate: float = 0.0


def analyze_reciprocity(
    conversation: Conversation,
    messages: list[Message],
    session_gap_hours: int = DEFAULT_SESSION_GAP_HOURS,
) -> ReciprocityResult:
    """Analyse conversation balance — who initiates, replies faster, writes more, closes?

    A *session* is a burst of messages where consecutive messages are at most
    ``session_gap_hours`` apart.  Sessions are the unit for initiation/closure stats.

    Args:
        conversation: The Conversation container (unused; future extensibility).
        messages: All messages, in any order.
        session_gap_hours: Gap (in hours) that triggers a new session.

    Returns:
        A ReciprocityResult with all balance metrics.
    """
    if not messages:
        return ReciprocityResult()

    sorted_msgs = sorted(messages, key=lambda m: m.timestamp)
    gap_threshold = timedelta(hours=session_gap_hours)

    # Partition into sessions
    sessions: list[list[Message]] = []
    current_session: list[Message] = [sorted_msgs[0]]
    for i in range(1, len(sorted_msgs)):
        gap = sorted_msgs[i].timestamp - sorted_msgs[i - 1].timestamp
        if gap > gap_threshold:
            sessions.append(current_session)
            current_session = [sorted_msgs[i]]
        else:
            current_session.append(sorted_msgs[i])
    sessions.append(current_session)

    # ── initiation & closure ─────────────────────────────
    me_starts = 0
    contact_starts = 0
    me_ends = 0
    contact_ends = 0

    for sess in sessions:
        if sess[0].sender == Sender.ME:
            me_starts += 1
        else:
            contact_starts += 1
        if sess[-1].sender == Sender.ME:
            me_ends += 1
        else:
            contact_ends += 1

    n_sessions = len(sessions)
    me_initiation_rate = me_starts / n_sessions
    contact_initiation_rate = contact_starts / n_sessions
    me_closure_rate = me_ends / n_sessions
    contact_closure_rate = contact_ends / n_sessions

    # ── reply times ──────────────────────────────────────
    me_reply_times: list[float] = []
    contact_reply_times: list[float] = []

    for sess in sessions:
        for i in range(1, len(sess)):
            prev = sess[i - 1]
            cur = sess[i]
            if prev.sender != cur.sender:
                delta = (cur.timestamp - prev.timestamp).total_seconds()
                if cur.sender == Sender.ME:
                    me_reply_times.append(delta)
                else:
                    contact_reply_times.append(delta)

    me_reply_avg = _safe_avg(me_reply_times)
    contact_reply_avg = _safe_avg(contact_reply_times)

    # ── message lengths ──────────────────────────────────
    me_lengths = [len(m.content) for m in sorted_msgs if m.sender == Sender.ME]
    contact_lengths = [len(m.content) for m in sorted_msgs if m.sender == Sender.CONTACT]
    me_avg_length = _safe_avg(me_lengths)
    contact_avg_length = _safe_avg(contact_lengths)

    return ReciprocityResult(
        me_initiation_rate=round(me_initiation_rate, 4),
        contact_initiation_rate=round(contact_initiation_rate, 4),
        me_reply_avg_seconds=round(me_reply_avg, 1),
        contact_reply_avg_seconds=round(contact_reply_avg, 1),
        me_avg_length=round(me_avg_length, 1),
        contact_avg_length=round(contact_avg_length, 1),
        me_closure_rate=round(me_closure_rate, 4),
        contact_closure_rate=round(contact_closure_rate, 4),
    )


def _safe_avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)
