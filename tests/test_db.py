from __future__ import annotations

from datetime import timedelta

import pytest

from bot.db import Database
from tests.conftest import dt


@pytest.mark.asyncio
async def test_create_and_list_booking(db: Database) -> None:
    starts = dt("2026-11-10", "10:00")
    ends = starts + timedelta(minutes=45)
    booking = await db.create_booking(
        user_id=42,
        client_name="Олена",
        phone="+380501112233",
        service_id="haircut",
        service_name="Стрижка",
        duration_minutes=45,
        starts_at=starts,
        ends_at=ends,
    )
    assert booking is not None
    assert booking.id > 0
    listed = await db.list_user_bookings(42, upcoming_only=False)
    assert len(listed) == 1
    assert listed[0].client_name == "Олена"


@pytest.mark.asyncio
async def test_overlap_rejected(db: Database) -> None:
    starts = dt("2026-11-10", "11:00")
    ends = starts + timedelta(minutes=60)
    first = await db.create_booking(
        user_id=1,
        client_name="A",
        phone="+380501111111",
        service_id="a",
        service_name="A",
        duration_minutes=60,
        starts_at=starts,
        ends_at=ends,
    )
    assert first is not None
    # Overlapping: 11:30-12:30
    second = await db.create_booking(
        user_id=2,
        client_name="B",
        phone="+380502222222",
        service_id="b",
        service_name="B",
        duration_minutes=60,
        starts_at=starts + timedelta(minutes=30),
        ends_at=ends + timedelta(minutes=30),
    )
    assert second is None


@pytest.mark.asyncio
async def test_cancel_booking(db: Database) -> None:
    starts = dt("2026-11-11", "09:00")
    ends = starts + timedelta(minutes=30)
    booking = await db.create_booking(
        user_id=7,
        client_name="C",
        phone="+380503333333",
        service_id="c",
        service_name="C",
        duration_minutes=30,
        starts_at=starts,
        ends_at=ends,
    )
    assert booking is not None
    cancelled = await db.cancel_booking(booking.id, by_user_id=7)
    assert cancelled is not None
    assert cancelled.status == "cancelled"
    # Wrong user cannot cancel
    again = await db.create_booking(
        user_id=7,
        client_name="C",
        phone="+380503333333",
        service_id="c",
        service_name="C",
        duration_minutes=30,
        starts_at=starts + timedelta(hours=2),
        ends_at=ends + timedelta(hours=2),
    )
    assert again is not None
    denied = await db.cancel_booking(again.id, by_user_id=999)
    assert denied is None


@pytest.mark.asyncio
async def test_block_affects_busy_ranges(db: Database) -> None:
    starts = dt("2026-11-12", "00:00")
    ends = dt("2026-11-13", "00:00")
    await db.add_block(starts, ends, reason="day off extra")
    ranges = await db.active_ranges_for_day("2026-11-12")
    assert len(ranges) == 1
    assert ranges[0].start == starts


@pytest.mark.asyncio
async def test_list_bookings_for_day(db: Database) -> None:
    await db.create_booking(
        user_id=1,
        client_name="D",
        phone="+380504444444",
        service_id="d",
        service_name="D",
        duration_minutes=30,
        starts_at=dt("2026-11-15", "14:00"),
        ends_at=dt("2026-11-15", "14:30"),
    )
    await db.create_booking(
        user_id=1,
        client_name="E",
        phone="+380505555555",
        service_id="e",
        service_name="E",
        duration_minutes=30,
        starts_at=dt("2026-11-16", "14:00"),
        ends_at=dt("2026-11-16", "14:30"),
    )
    day = await db.list_bookings_for_day("2026-11-15")
    assert len(day) == 1
    assert day[0].client_name == "D"
