from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from bot.config import BusinessConfig
from bot.slots import TimeRange, available_dates, generate_slots, is_day_off, parse_block_input

TZ = ZoneInfo("Europe/Kyiv")


def test_days_off_and_weekend(simple_biz: BusinessConfig) -> None:
    # 2026-11-02 is Monday (open), 2026-11-03 Tuesday listed in days_off, 2026-11-08 Sunday
    assert not is_day_off(simple_biz, date(2026, 11, 2))
    assert is_day_off(simple_biz, date(2026, 11, 3))
    assert is_day_off(simple_biz, date(2026, 11, 8))  # no Sunday hours


def test_available_dates_skips_offs(simple_biz: BusinessConfig) -> None:
    dates = available_dates(simple_biz, today=date(2026, 11, 2))
    assert date(2026, 11, 2) in dates  # Mon
    assert date(2026, 11, 3) not in dates  # day off
    assert date(2026, 11, 8) not in dates  # Sunday
    assert all(d >= date(2026, 11, 2) for d in dates)
    assert len(dates) <= simple_biz.booking_horizon_days


def test_generate_respects_hours_and_duration(simple_biz: BusinessConfig) -> None:
    day = date(2026, 11, 2)  # Mon 09-12
    now = datetime(2026, 11, 2, 8, 0, tzinfo=TZ)
    slots = generate_slots(simple_biz, day, 60, now=now)
    # Last start that fits 60 min before 12:00 is 11:00
    assert slots[0] == datetime(2026, 11, 2, 9, 0, tzinfo=TZ)
    assert slots[-1] == datetime(2026, 11, 2, 11, 0, tzinfo=TZ)
    assert all(s + timedelta(minutes=60) <= datetime(2026, 11, 2, 12, 0, tzinfo=TZ) for s in slots)


def test_generate_skips_past(simple_biz: BusinessConfig) -> None:
    day = date(2026, 11, 2)
    now = datetime(2026, 11, 2, 10, 15, tzinfo=TZ)
    slots = generate_slots(simple_biz, day, 30, now=now)
    assert all(s >= now for s in slots)
    assert datetime(2026, 11, 2, 9, 0, tzinfo=TZ) not in slots
    assert datetime(2026, 11, 2, 10, 0, tzinfo=TZ) not in slots
    assert datetime(2026, 11, 2, 10, 30, tzinfo=TZ) in slots


def test_generate_skips_overlaps(simple_biz: BusinessConfig) -> None:
    day = date(2026, 11, 2)
    now = datetime(2026, 11, 2, 8, 0, tzinfo=TZ)
    existing = [
        TimeRange(
            datetime(2026, 11, 2, 9, 30, tzinfo=TZ),
            datetime(2026, 11, 2, 10, 30, tzinfo=TZ),
        )
    ]
    slots = generate_slots(simple_biz, day, 60, existing=existing, now=now)
    # 09:00 overlaps (ends 10:00 overlaps 9:30-10:30)
    assert datetime(2026, 11, 2, 9, 0, tzinfo=TZ) not in slots
    assert datetime(2026, 11, 2, 9, 30, tzinfo=TZ) not in slots
    assert datetime(2026, 11, 2, 10, 0, tzinfo=TZ) not in slots
    assert datetime(2026, 11, 2, 10, 30, tzinfo=TZ) in slots


def test_generate_skips_blocks(simple_biz: BusinessConfig) -> None:
    day = date(2026, 11, 2)
    now = datetime(2026, 11, 2, 8, 0, tzinfo=TZ)
    blocks = [
        TimeRange(
            datetime(2026, 11, 2, 0, 0, tzinfo=TZ),
            datetime(2026, 11, 3, 0, 0, tzinfo=TZ),
        )
    ]
    slots = generate_slots(simple_biz, day, 30, blocks=blocks, now=now)
    assert slots == []


def test_generate_empty_on_day_off(simple_biz: BusinessConfig) -> None:
    slots = generate_slots(
        simple_biz,
        date(2026, 11, 3),
        30,
        now=datetime(2026, 11, 3, 8, 0, tzinfo=TZ),
    )
    assert slots == []


def test_parse_block_full_day() -> None:
    tr = parse_block_input("2026-11-01", "Europe/Kyiv")
    assert tr is not None
    assert tr.start.date() == date(2026, 11, 1)
    assert (tr.end - tr.start) == timedelta(days=1)


def test_parse_block_range() -> None:
    tr = parse_block_input("2026-11-01 14:00 — 2026-11-01 16:00", "Europe/Kyiv")
    assert tr is not None
    assert tr.start.hour == 14
    assert tr.end.hour == 16


def test_time_range_overlaps() -> None:
    a = TimeRange(
        datetime(2026, 1, 1, 10, 0, tzinfo=TZ),
        datetime(2026, 1, 1, 11, 0, tzinfo=TZ),
    )
    b = TimeRange(
        datetime(2026, 1, 1, 10, 30, tzinfo=TZ),
        datetime(2026, 1, 1, 11, 30, tzinfo=TZ),
    )
    c = TimeRange(
        datetime(2026, 1, 1, 11, 0, tzinfo=TZ),
        datetime(2026, 1, 1, 12, 0, tzinfo=TZ),
    )
    assert a.overlaps(b)
    assert not a.overlaps(c)
