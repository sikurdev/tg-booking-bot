"""Slot generation: working hours, duration, overlaps, past times, days off, blocks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from bot.config import BusinessConfig


@dataclass(frozen=True)
class TimeRange:
    start: datetime
    end: datetime

    def overlaps(self, other: TimeRange) -> bool:
        return self.start < other.end and other.start < self.end


def _parse_hhmm(value: str) -> time:
    h, m = value.split(":")
    return time(int(h), int(m))


def _combine(d: date, t: time, tz: ZoneInfo) -> datetime:
    return datetime(d.year, d.month, d.day, t.hour, t.minute, tzinfo=tz)


def is_day_off(biz: BusinessConfig, d: date) -> bool:
    if d.isoformat() in biz.days_off:
        return True
    return d.weekday() not in biz.working_hours


def available_dates(
    biz: BusinessConfig,
    *,
    today: date | None = None,
    tz_name: str | None = None,
) -> list[date]:
    tz = ZoneInfo(tz_name or biz.timezone)
    if today is None:
        today = datetime.now(tz).date()
    out: list[date] = []
    for i in range(biz.booking_horizon_days):
        d = today + timedelta(days=i)
        if not is_day_off(biz, d):
            out.append(d)
    return out


def generate_slots(
    biz: BusinessConfig,
    day: date,
    duration_minutes: int,
    *,
    existing: list[TimeRange] | None = None,
    blocks: list[TimeRange] | None = None,
    now: datetime | None = None,
    tz_name: str | None = None,
) -> list[datetime]:
    """Return free slot starts for a day.

    - Uses working hours for the weekday.
    - Steps by slot_step_minutes.
    - Slot of `duration_minutes` must finish by close.
    - Skips overlaps with existing bookings and blocks.
    - Skips starts in the past (relative to `now`).
    - Returns [] for days off / missing hours.
    """
    tz = ZoneInfo(tz_name or biz.timezone)
    if now is None:
        now = datetime.now(tz)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=tz)

    if is_day_off(biz, day):
        return []

    hours = biz.working_hours.get(day.weekday())
    if hours is None:
        return []

    open_t = _parse_hhmm(hours.open)
    close_t = _parse_hhmm(hours.close)
    open_dt = _combine(day, open_t, tz)
    close_dt = _combine(day, close_t, tz)
    if close_dt <= open_dt:
        return []

    step = timedelta(minutes=biz.slot_step_minutes)
    duration = timedelta(minutes=duration_minutes)
    busy = list(existing or []) + list(blocks or [])

    slots: list[datetime] = []
    cursor = open_dt
    while cursor + duration <= close_dt:
        if cursor >= now:
            candidate = TimeRange(cursor, cursor + duration)
            if not any(candidate.overlaps(b) for b in busy):
                slots.append(cursor)
        cursor += step
    return slots


def parse_block_input(text: str, tz_name: str = "Europe/Kyiv") -> TimeRange | None:
    """Parse 'YYYY-MM-DD' (full day) or 'YYYY-MM-DD HH:MM — YYYY-MM-DD HH:MM'."""
    tz = ZoneInfo(tz_name)
    raw = text.strip().replace("—", "-").replace("–", "-")
    # Full day
    if len(raw) == 10 and raw.count("-") == 2:
        try:
            d = date.fromisoformat(raw)
        except ValueError:
            return None
        start = datetime(d.year, d.month, d.day, 0, 0, tzinfo=tz)
        end = start + timedelta(days=1)
        return TimeRange(start, end)

    # Range with optional separators
    for sep in (" - ", " — ", " – ", " to "):
        if sep in text:
            left, right = text.split(sep, 1)
            break
    else:
        parts = raw.split()
        if len(parts) == 4:
            left = f"{parts[0]} {parts[1]}"
            right = f"{parts[2]} {parts[3]}"
        else:
            return None

    def parse_dt(s: str) -> datetime | None:
        s = s.strip()
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(s, fmt)
                if fmt == "%Y-%m-%d":
                    dt = datetime(dt.year, dt.month, dt.day, 0, 0)
                return dt.replace(tzinfo=tz)
            except ValueError:
                continue
        return None

    start = parse_dt(left)
    end = parse_dt(right)
    if start is None or end is None or end <= start:
        return None
    return TimeRange(start, end)
