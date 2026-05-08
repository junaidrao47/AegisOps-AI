from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class TimelineEvent:
    occurred_at: datetime
    title: str
    detail: str | None = None
    source: str = "auto"


_TS_PATTERNS: list[re.Pattern[str]] = [
    # 12:03 or 12:03:44
    re.compile(r"(?P<h>\d{2}):(?P<m>\d{2})(?::(?P<s>\d{2}))?"),
    # 2026-05-09 12:03:44 or 2026-05-09T12:03:44Z
    re.compile(
        r"(?P<Y>\d{4})-(?P<M>\d{2})-(?P<D>\d{2})[T ](?P<h>\d{2}):(?P<m>\d{2})(?::(?P<s>\d{2}))?(?:\.\d+)?(?P<z>Z)?"
    ),
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(line: str, base_date: datetime | None) -> datetime | None:
    for pat in _TS_PATTERNS:
        m = pat.search(line)
        if not m:
            continue
        gd = m.groupdict()
        try:
            if gd.get("Y"):
                dt = datetime(
                    int(gd["Y"]),
                    int(gd["M"]),
                    int(gd["D"]),
                    int(gd["h"]),
                    int(gd["m"]),
                    int(gd.get("s") or 0),
                    tzinfo=timezone.utc,
                )
                return dt
            # time-only
            if base_date is None:
                return None
            dt = datetime(
                base_date.year,
                base_date.month,
                base_date.day,
                int(gd["h"]),
                int(gd["m"]),
                int(gd.get("s") or 0),
                tzinfo=timezone.utc,
            )
            return dt
        except Exception:
            return None
    return None


_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"deployment (started|begin)|starting deployment", re.I), "Deployment Started"),
    (re.compile(r"CrashLoopBackOff|pod .*crash|container .*crash", re.I), "Pod Crash Detected"),
    (re.compile(r"timeout|timed out|ETIMEDOUT|DB timeout", re.I), "DB Timeout Observed"),
    (re.compile(r"root cause|identified root cause|cause identified", re.I), "Root Cause Identified"),
]


def generate_timeline_from_text(text: str, *, base_date: datetime | None = None) -> list[TimelineEvent]:
    """Cheap timeline generator.

    Uses heuristic regex rules on log/text input and returns a sorted list of events.
    """

    events: list[TimelineEvent] = []
    seen: set[tuple[str, int]] = set()

    for idx, raw_line in enumerate(text.splitlines()):
        line = raw_line.strip()
        if not line:
            continue

        occurred_at = _parse_timestamp(line, base_date) or _now()

        for pat, title in _RULES:
            if not pat.search(line):
                continue

            key = (title, int(occurred_at.timestamp()))
            if key in seen:
                continue
            seen.add(key)

            detail = line
            events.append(TimelineEvent(occurred_at=occurred_at, title=title, detail=detail, source="auto"))

    # Stable sort by time then title
    events.sort(key=lambda e: (e.occurred_at, e.title))
    return events
